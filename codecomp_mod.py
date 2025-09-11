from pathlib import Path
from collections import Counter
import shutil, re, datetime as dt

def beautify_codecomp_html(codecomp_path: Path,
                           out_copy_at_run_root: Path,
                           old_label: str,               # LHS (Previous) folder name
                           new_label: str,               # RHS (Latest) folder name
                           new_counts: Counter,          # "New" per top-level metadata (case-insensitive)
                           modified_counts: Counter,     # "Modified" per top-level metadata (case-insensitive)
                           prev_human: str = None,       # e.g., "10th Aug 2025"  (optional)
                           latest_human: str = None):    # e.g., "4th Sept 2025" (optional)
    """
    Create a minimal, beautiful Diff-Only page:

      Header:
        - Title: "Code Comparison Report - Diff Only"
        - Badges: "LHS (Previous): <prev_human>  vs  RHS (Latest): <latest_human>"
        - Logo + Back chip

      Body:
        - Single table: [Metadata Type | File Changes (Total) | New | Modified]
          * Metadata Type is a blue pill anchor linking to the per-type diff page.
          * Hrefs are parsed from the *raw* Beyond Compare HTML. If not found, fall back to codecomp_raw.html.

      Footer:
        - Stuck to end of page (flex column)

    Always writes the pretty page. Preserves original raw HTML as codecomp_raw.html (same dir + run-root alias).
    """

    # --- Read & preserve raw BC HTML (if present) ---
    raw_html = ""
    raw_in_same_dir = codecomp_path.with_name("codecomp_raw.html")
    raw_alias_at_root = None
    try:
        if codecomp_path.exists():
            raw_html = codecomp_path.read_text(encoding="utf-8", errors="ignore")
            # Keep raw beside pretty
            shutil.copy2(codecomp_path, raw_in_same_dir)
            # Also expose raw at run root (next to pretty alias)
            if out_copy_at_run_root:
                raw_alias_at_root = out_copy_at_run_root.parent / "codecomp_raw.html"
                raw_alias_at_root.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(codecomp_path, raw_alias_at_root)
    except Exception:
        # Non-fatal; we still render pretty page
        pass

    # --- Parse any <a href="...">text</a> entries from raw to map metadata -> per-type page ---
    # Example raw line: <a href="Previous_dump_vs_Latest_Dump/codecomp/classes/classes.html">classes</a><br/>
    anchor_pairs = re.findall(r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', raw_html or "", flags=re.I | re.S)
    href_by_meta_lower = {}
    for href, label in anchor_pairs:
        meta_txt = re.sub(r"\s+", " ", label).strip()
        if not meta_txt:
            continue
        href_by_meta_lower[meta_txt.lower()] = href

    # --- Build a stable set of metadata keys (union of counters and anchors) ---
    # Normalize counters to lower keys for reliable lookup
    n_l = {str(k).lower(): int(v) for k, v in (new_counts or {}).items()}
    m_l = {str(k).lower(): int(v) for k, v in (modified_counts or {}).items()}
    keys = set(n_l.keys()) | set(m_l.keys()) | set(href_by_meta_lower.keys())
    metas_sorted = sorted(keys, key=lambda s: s.lower())

    # Determine how the pretty page will resolve the *fallback* raw page
    open_target = "codecomp_raw.html" if codecomp_path.parent.name == "codecomp" else "./codecomp_raw.html"

    def row(meta_key_lower: str) -> str:
        label = meta_key_lower  # show as-is first; optionally prettify
        # prefer the original label casing if we saw it in anchors
        for _href, _label in anchor_pairs:
            if _label.strip().lower() == meta_key_lower:
                label = _label.strip()
                break

        new_n = n_l.get(meta_key_lower, 0)
        mod_n = m_l.get(meta_key_lower, 0)
        tot_n = new_n + mod_n

        # If we parsed a per-type href, use it; else fall back to opening the raw page
        href = href_by_meta_lower.get(meta_key_lower)
        if href:
            meta_cell = f'<a class="meta-btn" href="{href}" target="_blank" rel="noopener">{label}</a>'
        else:
            # Fallback: open raw page; no deep link but at least shows the BC content
            meta_cell = f'<a class="meta-btn" href="{open_target}" target="_blank" rel="noopener">{label}</a>'

        return (
            f"<tr>"
            f"  <td>{meta_cell}</td>"
            f'  <td><span class="num black">{tot_n}</span></td>'
            f'  <td><span class="num green">{new_n}</span></td>'
            f'  <td><span class="num orange">{mod_n}</span></td>'
            f"</tr>"
        )

    rows_html = (
        "\n".join(row(k) for k in metas_sorted)
        if metas_sorted else '<tr><td colspan="4" class="empty">No differences detected.</td></tr>'
    )

    # --- Human-friendly badges (auto-derive if not provided) ---
    def _parse_token_to_human(name: str) -> str:
        # fallbacks if caller didn't pass prev_human/latest_human
        m = re.search(r'(\d{1,2})(?:st|nd|rd|th)?([A-Za-z]+)(\d{4})', name)
        if not m:
            return name
        day = int(m.group(1))
        mon = m.group(2).lower()
        year = int(m.group(3))
        month_map = {"jan": "Jan", "feb": "Feb", "mar": "Mar", "apr":"Apr", "may":"May",
                     "jun":"Jun","jul":"Jul","aug":"Aug","sep":"Sept","sept":"Sept","oct":"Oct","nov":"Nov","dec":"Dec"}
        for key in ("sept","sep","jan","feb","mar","apr","may","jun","jul","aug","oct","nov","dec"):
            if mon.startswith(key):
                mon_h = "Sept" if key in ("sep","sept") else month_map[key]
                break
        else:
            return name
        suffix = "th" if 11 <= day % 100 <= 13 else {1:"st",2:"nd",3:"rd"}.get(day % 10, "th")
        return f"{day}{suffix} {mon_h} {year}"

    lhs_badge = prev_human or _parse_token_to_human(old_label)
    rhs_badge = latest_human or _parse_token_to_human(new_label)

    # --- Pretty HTML with sticky footer ---
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Code Comparison Report - Diff Only — {old_label} vs {new_label}</title>
<style>
  :root{{ --blue:#1d4ed8; --blue-deep:#1e40af; --green:#16a34a; --orange:#d97706;
         --gray:#6b7280; --ink:#0b0f19; --line:#e6e9ef; --bg:#f8fafc; --white:#fff;
         --radius:16px; --shadow:0 8px 24px rgba(0,0,0,.08),0 2px 6px rgba(0,0,0,.06); }}
  *,*::before,*::after{{box-sizing:border-box}}
  html, body{{height:100%}}
  body{{margin:0; background:var(--bg); color:var(--ink); font:14px/1.5 system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Cantarell,Noto Sans,sans-serif;
        display:flex; flex-direction:column; min-height:100vh;}}

  header{{background:linear-gradient(135deg,#0b0f19 0%,var(--blue-deep) 100%); color:#fff}}
  .h-inner{{max-width:1100px; margin:0 auto; padding:14px 18px; display:flex; align-items:center; justify-content:space-between; gap:12px}}
  .h-title{{display:flex; flex-direction:column; gap:6px}}
  .h-title h1{{margin:0; font-size:clamp(18px,2.2vw,24px); font-weight:900; letter-spacing:.2px}}
  .badges{{display:flex; gap:8px; flex-wrap:wrap}}
  .badge{{background:rgba(255,255,255,.14); border:1px solid rgba(255,255,255,.28); color:#fff; padding:4px 10px; border-radius:999px; font-size:12px}}
  .brand{{display:flex; align-items:center; gap:8px}}
  .brand img{{height:32px; display:block; filter:drop-shadow(0 2px 2px rgba(0,0,0,.35))}}
  .back{{display:inline-flex; align-items:center; gap:6px; font-weight:700; font-size:12px;
         background:rgba(255,255,255,.10); border:1px solid rgba(255,255,255,.35);
         border-radius:999px; padding:4px 8px; color:#fff; text-decoration:none}}
  .back:hover{{background:rgba(255,255,255,.18)}}

  main{{max-width:1100px; margin:18px auto; padding:0 18px; flex:1 0 auto;}}
  .card{{background:#fff; border:1px solid var(--line); border-radius:var(--radius); box-shadow:var(--shadow); padding:18px}}

  table.summary{{width:100%; border-collapse:separate; border-spacing:0 10px}}
  table.summary th, table.summary td{{text-align:left; padding:10px 12px}}
  table.summary thead th{{font-size:12px; color:#111; letter-spacing:.3px; border-bottom:1px solid var(--line)}}
  table.summary tbody tr{{background:#fff; border:1px solid var(--line)}}
  table.summary tbody td{{border-top:1px solid var(--line); border-bottom:1px solid var(--line)}}
  table.summary tbody tr td:first-child{{border-left:1px solid var(--line); border-top-left-radius:12px; border-bottom-left-radius:12px}}
  table.summary tbody tr td:last-child{{border-right:1px solid var(--line); border-top-right-radius:12px; border-bottom-right-radius:12px}}

  /* Anchor styled like a button */
  .meta-btn{{ background:var(--blue); color:#fff; text-decoration:none; display:inline-block;
              border-radius:999px; padding:8px 12px; font-weight:800; box-shadow:0 2px 6px rgba(0,0,0,.12);
              transition:transform .15s ease, box-shadow .15s ease, filter .15s ease; }}
  .meta-btn:hover{{ transform:translateY(-1px); box-shadow:0 6px 14px rgba(0,0,0,.18); filter:brightness(1.05); }}

  .num{{display:inline-block; min-width:30px; text-align:center; font-weight:900}}
  .num.black{{color:#111}} .num.green{{color:var(--green)}} .num.orange{{color:var(--orange)}}
  .empty{{text-align:center; color:#6b7280}}

  footer{{background:#0b0f19; color:#fff; text-align:center; font-size:12px; padding:6px 10px; margin-top:auto}}
</style>
</head>
<body>
<header>
  <div class="h-inner">
    <div class="h-title">
      <h1>Code Comparison Report - Diff Only</h1>
      <div class="badges">
        <span class="badge">LHS (Previous): <strong>{lhs_badge}</strong></span>
        <span class="badge">vs</span>
        <span class="badge">RHS (Latest): <strong>{rhs_badge}</strong></span>
      </div>
    </div>
    <div class="brand">
      <img src="../assets/cadence-logo.png" alt="Cadence logo" />
      <a class="back" href="./index.html">← Back</a>
    </div>
  </div>
</header>

<main>
  <section class="card">
    <table class="summary" aria-label="Summary by Metadata Type">
      <thead>
        <tr>
          <th>Metadata Type</th>
          <th>File Changes (Total)</th>
          <th>New</th>
          <th>Modified</th>
        </tr>
      </thead>
      <tbody>
        {rows_html}
      </tbody>
    </table>
  </section>
</main>

<footer>This is the end of report.</footer>
</body>
</html>
"""

    # --- Write pretty page and alias ---
    codecomp_path.parent.mkdir(parents=True, exist_ok=True)
    codecomp_path.write_text(html, encoding="utf-8")
    if out_copy_at_run_root:
        out_copy_at_run_root.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(codecomp_path, out_copy_at_run_root)
