#!/usr/bin/env python3
"""
Profile Comparison Automation

Usage:
  python3 profile_comp.py Profile_Comp.conf

What it does (per your requirement):
1) Read source_path, destination_path, Release_Name from conf.
2) Copy profiles from source_path + matching ones from destination_path to /tmp.
3) In each source profile:
   - Detect element blocks containing BOTH <readable> and <editable>.
   - Keep ONLY those block types (e.g., fieldPermissions, objectPermissions), delete others.
4) In each destination profile:
   - Keep ONLY the same block types that were found in the source version of that profile.
5) Extract rows and compare readable/editable values between sandbox(source) and prod(dest).
6) Generate a professional HTML report:
   /data/public/Profile_Comp_Report/{Release_Name}/index.html
7) Cleanup tmp workspace.

Notes:
- Handles Salesforce Profile XML namespace robustly.
- If a dest profile or matching permission block is missing, values are shown as "—" and treated as mismatch.
"""

import os
import re
import sys
import json
import shutil
from pathlib import Path
from datetime import datetime
import xml.etree.ElementTree as ET

# ----------------------------
# Config parsing
# ----------------------------
CONF_KEYS = ("source_path", "destination_path", "Release_Name")

def parse_conf(conf_path: str) -> dict:
    text = Path(conf_path).read_text(encoding="utf-8", errors="ignore")
    conf = {}
    for k in CONF_KEYS:
        # accepts: key="value" or key='value' or key=value
        m = re.search(rf'^\s*{re.escape(k)}\s*=\s*["\']?(.*?)["\']?\s*$', text, re.M)
        if not m:
            raise ValueError(f"Missing '{k}' in {conf_path}")
        conf[k] = m.group(1).strip()
    return conf

# ----------------------------
# XML helpers
# ----------------------------
NS = {"sf": "http://soap.sforce.com/2006/04/metadata"}

def local_name(tag: str) -> str:
    """Remove namespace from tag."""
    if tag.startswith("{"):
        return tag.split("}", 1)[1]
    return tag

def indent(elem, level=0):
    """Pretty-print indentation (ElementTree)."""
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        for child in elem:
            indent(child, level+1)
        if not child.tail or not child.tail.strip():
            child.tail = i
    if level and (not elem.tail or not elem.tail.strip()):
        elem.tail = i

def has_readable_editable(block: ET.Element) -> bool:
    """Check if a block has both readable & editable children."""
    kids = {local_name(c.tag) for c in list(block)}
    return "readable" in kids and "editable" in kids

IDENTIFIER_TAG_ORDER = [
    "field", "object", "recordType", "tab", "apexClass", "page",
    "application", "layout", "userLicense"
]

def get_identifier(block: ET.Element) -> str:
    """Find identifier child text to match src/dest blocks."""
    for t in IDENTIFIER_TAG_ORDER:
        node = block.find(f"sf:{t}", NS)
        if node is not None and (node.text or "").strip():
            return node.text.strip()
        # safety if no namespace on child
        for c in list(block):
            if local_name(c.tag) == t and (c.text or "").strip():
                return c.text.strip()
    # fallback: stable string based on children text excluding readable/editable
    parts = []
    for c in list(block):
        ln = local_name(c.tag)
        if ln in ("readable", "editable"):
            continue
        parts.append(f"{ln}={(c.text or '').strip()}")
    return "|".join(parts) or "(unknown)"

def get_bool_text(block: ET.Element, child_name: str):
    """Return 'true'/'false' as bool or None if missing."""
    node = block.find(f"sf:{child_name}", NS)
    if node is None:
        # try without namespace
        for c in list(block):
            if local_name(c.tag) == child_name:
                node = c
                break
    if node is None or node.text is None:
        return None
    val = node.text.strip().lower()
    if val in ("true", "false"):
        return val == "true"
    return None

def reduce_profile(src_xml_path: Path, out_path: Path):
    """
    Reduce a source profile:
    - detect labels that have readable+editable blocks
    - keep only those labels
    Returns:
      allowed_labels: set[str]
      blocks_by_label: dict[label][identifier] = block
    """
    tree = ET.parse(src_xml_path)
    root = tree.getroot()

    # Detect allowed labels (block types)
    allowed_labels = set()
    for child in list(root):
        if has_readable_editable(child):
            allowed_labels.add(local_name(child.tag))

    # Prune everything else
    for child in list(root):
        if local_name(child.tag) not in allowed_labels:
            root.remove(child)

    indent(root)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(out_path, encoding="UTF-8", xml_declaration=True)

    # Build blocks map for comparison
    blocks_by_label = {}
    for child in list(root):
        label = local_name(child.tag)
        ident = get_identifier(child)
        blocks_by_label.setdefault(label, {})[ident] = child

    return allowed_labels, blocks_by_label

def reduce_dest_profile(dest_xml_path: Path, out_path: Path, allowed_labels: set):
    """
    Reduce destination profile to only allowed_labels.
    Returns blocks_by_label similar to reduce_profile.
    """
    if not dest_xml_path.exists():
        # Create an empty Profile root with namespace
        ET.register_namespace("", NS["sf"])
        root = ET.Element(f"{{{NS['sf']}}}Profile")
        tree = ET.ElementTree(root)
    else:
        tree = ET.parse(dest_xml_path)
        root = tree.getroot()

    for child in list(root):
        if local_name(child.tag) not in allowed_labels:
            root.remove(child)

    indent(root)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(out_path, encoding="UTF-8", xml_declaration=True)

    blocks_by_label = {}
    for child in list(root):
        label = local_name(child.tag)
        ident = get_identifier(child)
        blocks_by_label.setdefault(label, {})[ident] = child

    return blocks_by_label

# ----------------------------
# Report generation
# ----------------------------
PASTEL_COLORS = [
    "#fff7d6", "#e9f7ef", "#eaf2ff", "#fce8ef", "#f3e8ff",
    "#e8fafc", "#f7f0e8", "#e9f9f1", "#f2f6d0", "#e7eef9",
    "#fdebd0", "#f9e7e7", "#eaf7d9", "#e8e8ff", "#f0fff0"
]

def mismatch_signature(rs, es, rp, ep):
    """
    Signature for mismatch categories.
    Treat None as a distinct value 'na'.
    """
    def norm(x):
        if x is None:
            return "na"
        return "true" if x else "false"
    return f"RS:{norm(rs)}|ES:{norm(es)}|RP:{norm(rp)}|EP:{norm(ep)}"

def build_rows(profile_name, src_blocks, dest_blocks, allowed_labels):
    rows = []
    for label in sorted(allowed_labels):
        src_map = src_blocks.get(label, {})
        dest_map = dest_blocks.get(label, {})

        for ident, sblock in src_map.items():
            rs = get_bool_text(sblock, "readable")
            es = get_bool_text(sblock, "editable")

            dblock = dest_map.get(ident)
            rp = get_bool_text(dblock, "readable") if dblock is not None else None
            ep = get_bool_text(dblock, "editable") if dblock is not None else None

            rows.append({
                "profile": profile_name,
                "label": label,
                "field": ident,
                "rs": rs,
                "es": es,
                "rp": rp,
                "ep": ep
            })
    return rows

def generate_html(rows, release_name, out_html_path: Path):
    # Determine mismatch categories and colors
    sig_to_color = {}
    for r in rows:
        sig = mismatch_signature(r["rs"], r["es"], r["rp"], r["ep"])
        if sig not in sig_to_color:
            sig_to_color[sig] = PASTEL_COLORS[len(sig_to_color) % len(PASTEL_COLORS)]
        r["sig"] = sig
        r["color"] = sig_to_color[sig]
        r["is_match"] = (r["rs"] == r["rp"]) and (r["es"] == r["ep"]) and (r["rs"] is not None) and (r["es"] is not None) and (r["rp"] is not None) and (r["ep"] is not None)

    # Legend items excluding perfect matches
    legend_items = [
        {"sig": sig, "color": color}
        for sig, color in sig_to_color.items()
        if "na" in sig or not all(
            part.split(":")[1] == sig.split("|")[0].split(":")[1]  # rough check not needed to be perfect
            for part in sig.split("|")
        )
    ]

    # Permission labels list
    labels = sorted({r["label"] for r in rows})

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    data_json = json.dumps(rows, ensure_ascii=False)
    labels_json = json.dumps(labels, ensure_ascii=False)
    legend_json = json.dumps(legend_items, ensure_ascii=False)

    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Profile Comparison Report - {release_name}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  :root {{
    --bg: #0b1020;
    --panel: #0f172a;
    --panel-2: #111b34;
    --ink: #e6ecff;
    --muted: #9db0d1;
    --accent: #2d6cdf;
    --accent-2:#00c2a8;
    --border: rgba(255,255,255,0.08);
    --good: #00d18c;
    --bad: #ffb703;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin:0; background: radial-gradient(1200px 700px at 10% -10%, #1e2a55 0%, transparent 60%), var(--bg);
    color: var(--ink); font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
  }}
  header {{
    position: sticky; top:0; z-index: 5;
    display:flex; align-items:center; gap:14px;
    padding:12px 16px; background: rgba(11,16,32,0.9); backdrop-filter: blur(8px);
    border-bottom:1px solid var(--border);
  }}
  .logo {{
    width:40px; height:40px; border-radius:10px;
    background: linear-gradient(145deg, #e6002d, #ff5c75);
    display:grid; place-items:center; font-weight:800; color:white; letter-spacing:0.5px;
  }}
  h1 {{ margin:0; font-size:20px; font-weight:700; }}
  .sub {{ font-size:12px; color: var(--muted); margin-top:2px; }}

  .wrap {{ padding:14px 16px 20px; max-width: 1400px; margin: 0 auto; }}
  .controls {{
    display:grid; grid-template-columns: 1.3fr 1fr 1fr 1fr;
    gap:10px; margin-bottom:12px;
  }}
  .card {{
    background: var(--panel); border:1px solid var(--border);
    border-radius:14px; padding:10px 12px; box-shadow: 0 6px 20px rgba(0,0,0,0.25);
  }}
  .control-label {{ font-size:12px; color:var(--muted); margin-bottom:6px; }}
  input[type="text"] {{
    width:100%; padding:9px 10px; border-radius:10px; border:1px solid var(--border);
    background: var(--panel-2); color:var(--ink);
    outline:none;
  }}
  select {{
    width:100%; padding:8px 10px; border-radius:10px; border:1px solid var(--border);
    background: var(--panel-2); color:var(--ink);
  }}
  .labels-box {{
    display:flex; flex-wrap:wrap; gap:6px; max-height:110px; overflow:auto; padding-top:4px;
  }}
  .chip {{
    font-size:12px; padding:6px 8px; border-radius:999px;
    background:#0e2447; border:1px solid var(--border); cursor:pointer; user-select:none;
  }}
  .chip.active {{ background: #1a3e78; border-color:#2a65c8; }}

  .legend {{
    display:flex; flex-wrap:wrap; gap:8px;
  }}
  .legend-item {{
    display:flex; align-items:center; gap:6px;
    font-size:12px; background: var(--panel-2); border:1px solid var(--border);
    padding:6px 8px; border-radius:999px; cursor:pointer;
  }}
  .dot {{
    width:10px; height:10px; border-radius:50%;
    border:1px solid rgba(0,0,0,0.15);
  }}
  .legend-item.active {{ outline: 2px solid var(--accent); }}

  table {{
    width:100%; border-collapse:separate; border-spacing:0;
    background: var(--panel); border:1px solid var(--border);
    border-radius:14px; overflow:hidden;
  }}
  thead th {{
    position: sticky; top:70px;
    background: #0b1530; color:#cfe0ff; font-size:12px; text-transform:uppercase; letter-spacing:0.06em;
    padding:10px 8px; border-bottom:1px solid var(--border);
  }}
  tbody td {{
    font-size:13px; padding:8px 8px; border-bottom:1px solid var(--border);
    color:#e8eeff;
  }}
  tbody tr:last-child td {{ border-bottom:none; }}
  tbody tr.match td {{ background: transparent; }}
  tbody tr.mismatch td {{ background: var(--rowcolor); }}

  .bool {{
    padding:2px 8px; border-radius:999px; font-weight:600; font-size:12px; display:inline-block;
  }}
  .t {{ background: rgba(0,209,140,0.15); color:#7fffd4; border:1px solid rgba(0,209,140,0.4); }}
  .f {{ background: rgba(255,255,255,0.06); color:#cfd8e8; border:1px solid var(--border); }}
  .na {{ background: rgba(255,183,3,0.15); color:#ffd166; border:1px solid rgba(255,183,3,0.35); }}

  footer {{
    margin-top:14px; padding:10px; text-align:center; font-size:12px; color:var(--muted);
  }}
  .muted {{ color:var(--muted); }}
  .count {{ font-weight:700; color:#fff; }}
  .right {{ margin-left:auto; font-size:12px; color:var(--muted); }}
</style>
</head>
<body>
<header>
  <div class="logo">CD</div>
  <div>
    <h1>Profile Comparison Report</h1>
    <div class="sub">Release: <b>{release_name}</b> &nbsp;|&nbsp; Generated: {generated_at}</div>
  </div>
  <div class="right" id="summary"></div>
</header>

<div class="wrap">
  <div class="controls">
    <div class="card">
      <div class="control-label">Search (Profile or Field)</div>
      <input id="searchBox" type="text" placeholder="Type profile name or field name...">
    </div>

    <div class="card">
      <div class="control-label">Permission Labels</div>
      <div class="labels-box" id="labelsBox"></div>
      <button id="clearLabels" style="margin-top:6px;padding:6px 8px;border-radius:8px;border:1px solid var(--border);background:var(--panel-2);color:var(--ink);cursor:pointer;">Clear Labels</button>
    </div>

    <div class="card">
      <div class="control-label">Boolean Palette</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;">
        <div>
          <div class="muted" style="font-size:11px;margin-bottom:4px;">Readable Sandbox</div>
          <select id="rsFilter">
            <option value="any">Any</option><option value="true">true</option><option value="false">false</option><option value="na">—</option>
          </select>
        </div>
        <div>
          <div class="muted" style="font-size:11px;margin-bottom:4px;">Editable Sandbox</div>
          <select id="esFilter">
            <option value="any">Any</option><option value="true">true</option><option value="false">false</option><option value="na">—</option>
          </select>
        </div>
        <div>
          <div class="muted" style="font-size:11px;margin-bottom:4px;">Readable Production</div>
          <select id="rpFilter">
            <option value="any">Any</option><option value="true">true</option><option value="false">false</option><option value="na">—</option>
          </select>
        </div>
        <div>
          <div class="muted" style="font-size:11px;margin-bottom:4px;">Editable Production</div>
          <select id="epFilter">
            <option value="any">Any</option><option value="true">true</option><option value="false">false</option><option value="na">—</option>
          </select>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="control-label">Mismatch Colors (click to filter)</div>
      <div class="legend" id="legendBox"></div>
      <button id="clearColors" style="margin-top:6px;padding:6px 8px;border-radius:8px;border:1px solid var(--border);background:var(--panel-2);color:var(--ink);cursor:pointer;">Clear Colors</button>
    </div>
  </div>

  <table>
    <thead>
      <tr>
        <th>Full Name of Profile</th>
        <th>Permission Label</th>
        <th>Field Name</th>
        <th>Readable Sandbox</th>
        <th>Editable Sandbox</th>
        <th>Readable Production</th>
        <th>Editable Production</th>
      </tr>
    </thead>
    <tbody id="tbody"></tbody>
  </table>

  <footer>
    Cadence Report Generated by Automation | SFDC_DevOps | devops_team@cadence.com |
  </footer>
</div>

<script>
const ROWS = {data_json};
const LABELS = {labels_json};
const LEGEND = {legend_json};

const searchBox = document.getElementById("searchBox");
const labelsBox = document.getElementById("labelsBox");
const legendBox = document.getElementById("legendBox");
const tbody = document.getElementById("tbody");
const summary = document.getElementById("summary");

const rsFilter = document.getElementById("rsFilter");
const esFilter = document.getElementById("esFilter");
const rpFilter = document.getElementById("rpFilter");
const epFilter = document.getElementById("epFilter");

let activeLabels = new Set();
let activeColors = new Set();

function boolToText(b) {{
  if (b === null || b === undefined) return "—";
  return b ? "true" : "false";
}}
function boolToClass(b) {{
  if (b === null || b === undefined) return "na";
  return b ? "t" : "f";
}}
function normBool(b) {{
  if (b === null || b === undefined) return "na";
  return b ? "true" : "false";
}}

function buildLabelChips() {{
  labelsBox.innerHTML = "";
  LABELS.forEach(l => {{
    const chip = document.createElement("div");
    chip.className = "chip";
    chip.textContent = l;
    chip.onclick = () => {{
      if (activeLabels.has(l)) {{
        activeLabels.delete(l); chip.classList.remove("active");
      }} else {{
        activeLabels.add(l); chip.classList.add("active");
      }}
      render();
    }};
    labelsBox.appendChild(chip);
  }});
}}
function buildLegend() {{
  legendBox.innerHTML = "";
  LEGEND.forEach(item => {{
    const el = document.createElement("div");
    el.className = "legend-item";
    el.dataset.sig = item.sig;

    const dot = document.createElement("div");
    dot.className = "dot";
    dot.style.background = item.color;

    const text = document.createElement("div");
    text.textContent = item.sig.replaceAll("|", "  ");

    el.appendChild(dot);
    el.appendChild(text);

    el.onclick = () => {{
      const sig = item.sig;
      if (activeColors.has(sig)) {{
        activeColors.delete(sig); el.classList.remove("active");
      }} else {{
        activeColors.add(sig); el.classList.add("active");
      }}
      render();
    }};
    legendBox.appendChild(el);
  }});
}}

function passesFilters(r) {{
  const q = searchBox.value.trim().toLowerCase();
  if (q) {{
    const hay = (r.profile + " " + r.field).toLowerCase();
    if (!hay.includes(q)) return false;
  }}
  if (activeLabels.size && !activeLabels.has(r.label)) return false;

  const rs = normBool(r.rs), es = normBool(r.es), rp = normBool(r.rp), ep = normBool(r.ep);
  if (rsFilter.value !== "any" && rsFilter.value !== rs) return false;
  if (esFilter.value !== "any" && esFilter.value !== es) return false;
  if (rpFilter.value !== "any" && rpFilter.value !== rp) return false;
  if (epFilter.value !== "any" && epFilter.value !== ep) return false;

  if (activeColors.size) {{
    if (!activeColors.has(r.sig)) return false;
  }}

  return true;
}}

function render() {{
  tbody.innerHTML = "";
  let shown=0, mism=0;

  ROWS.forEach(r => {{
    if (!passesFilters(r)) return;
    shown++;
    const tr = document.createElement("tr");

    const isMatch = (r.rs===r.rp) && (r.es===r.ep) && r.rs!==null && r.es!==null && r.rp!==null && r.ep!==null;
    if (!isMatch) {{
      mism++;
      tr.className = "mismatch";
      tr.style.setProperty("--rowcolor", r.color);
    }} else {{
      tr.className = "match";
    }}

    tr.innerHTML = `
      <td>${{r.profile}}</td>
      <td>${{r.label}}</td>
      <td style="font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;">${{r.field}}</td>
      <td><span class="bool ${{boolToClass(r.rs)}}">${{boolToText(r.rs)}}</span></td>
      <td><span class="bool ${{boolToClass(r.es)}}">${{boolToText(r.es)}}</span></td>
      <td><span class="bool ${{boolToClass(r.rp)}}">${{boolToText(r.rp)}}</span></td>
      <td><span class="bool ${{boolToClass(r.ep)}}">${{boolToText(r.ep)}}</span></td>
    `;
    tbody.appendChild(tr);
  }});

  summary.innerHTML = `Rows: <span class="count">${{shown}}</span> &nbsp;|&nbsp; Mismatches: <span class="count" style="color:#ffd166">${{mism}}</span>`;
}}

[searchBox, rsFilter, esFilter, rpFilter, epFilter].forEach(el => el.addEventListener("input", render));
document.getElementById("clearLabels").onclick = () => {{
  activeLabels.clear();
  document.querySelectorAll(".chip").forEach(c => c.classList.remove("active"));
  render();
}};
document.getElementById("clearColors").onclick = () => {{
  activeColors.clear();
  document.querySelectorAll(".legend-item").forEach(c => c.classList.remove("active"));
  render();
}};

buildLabelChips();
buildLegend();
render();
</script>
</body>
</html>
"""
    out_html_path.parent.mkdir(parents=True, exist_ok=True)
    out_html_path.write_text(html, encoding="utf-8")

# ----------------------------
# Main orchestration
# ----------------------------
def main():
    if len(sys.argv) < 2:
        print("Usage: python3 profile_comp.py Profile_Comp.conf")
        sys.exit(1)

    conf_path = sys.argv[1]
    conf = parse_conf(conf_path)

    source_path = Path(conf["source_path"]).expanduser().resolve()
    dest_path = Path(conf["destination_path"]).expanduser().resolve()
    release_name = conf["Release_Name"]

    if not source_path.is_dir():
        raise SystemExit(f"source_path not found: {source_path}")
    if not dest_path.is_dir():
        raise SystemExit(f"destination_path not found: {dest_path}")

    # Workspace under /tmp
    base_tmp = Path("/tmp") / f"Profile_Comp_Work_{release_name}"
    tmp_src = base_tmp / "source"
    tmp_dst = base_tmp / "dest"
    tmp_clean_src = base_tmp / "clean_source"
    tmp_clean_dst = base_tmp / "clean_dest"

    if base_tmp.exists():
        shutil.rmtree(base_tmp)
    tmp_src.mkdir(parents=True, exist_ok=True)
    tmp_dst.mkdir(parents=True, exist_ok=True)

    # Copy only profiles present in source
    profile_files = sorted([p for p in source_path.iterdir() if p.is_file() and p.name.endswith(".profile-meta.xml")])

    if not profile_files:
        raise SystemExit(f"No .profile-meta.xml files found in source_path: {source_path}")

    for sp in profile_files:
        shutil.copy2(sp, tmp_src / sp.name)
        dp = dest_path / sp.name
        if dp.exists():
            shutil.copy2(dp, tmp_dst / sp.name)
        else:
            # still create placeholder in tmp_dst for missing dest
            (tmp_dst / sp.name).write_text('<?xml version="1.0" encoding="UTF-8"?><Profile xmlns="http://soap.sforce.com/2006/04/metadata"/>', encoding="utf-8")

    all_rows = []

    for sp in profile_files:
        src_tmp_file = tmp_src / sp.name
        dst_tmp_file = tmp_dst / sp.name

        cleaned_src_file = tmp_clean_src / sp.name
        cleaned_dst_file = tmp_clean_dst / sp.name

        allowed_labels, src_blocks = reduce_profile(src_tmp_file, cleaned_src_file)
        dest_blocks = reduce_dest_profile(dst_tmp_file, cleaned_dst_file, allowed_labels)

        rows = build_rows(sp.name, src_blocks, dest_blocks, allowed_labels)
        all_rows.extend(rows)

    # Output HTML
    out_dir = Path("/data/public/Profile_Comp_Report") / release_name
    out_html = out_dir / "index.html"
    generate_html(all_rows, release_name, out_html)

    # Cleanup tmp
    shutil.rmtree(base_tmp, ignore_errors=True)

    print(f"Report generated: {out_html}")

if __name__ == "__main__":
    main()
