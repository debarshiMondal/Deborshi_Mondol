#!/usr/bin/env python3
import sys
import os
import re
import html
import csv
import subprocess
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime, timezone

# --------------------------------------------------------------------
# Original Combined PMD Report (HTML + CSVs)
# - Inputs:
#     PMDReport/orgpmdoutput/src/classes/*.txt
#     PMDReport/orgpmdoutput/src/triggers/*.txt
# - Outputs to: /data/public/PMDOUTPUT/$ENV/
#     index.html
#     Original_Combined_PMD_Report.csv
#     Original_Combined_PMD_Report_Classes.csv
#     Original_Combined_PMD_Report_Triggers.csv
# - Each row links to: <Name>_orgpmd.html
# --------------------------------------------------------------------

OUTPUT_ROOT = "/data/public/PMDOUTPUT"

PMD_CLASSES_DIR = "PMDReport/orgpmdoutput/src/classes"
PMD_TRIGGERS_DIR = "PMDReport/orgpmdoutput/src/triggers"
PMD_HIGH_PATTERNS_FILE = "build/property/pmd_high_patterns.txt"

# Real git-tracked paths
GIT_CLASSES_DIR = "src/classes"
GIT_TRIGGERS_DIR = "src/triggers"


@dataclass
class Issue:
    pattern: str
    message: str
    line_no: Optional[int]
    is_high: bool


@dataclass
class Item:
    kind: str  # "Class" or "Trigger"
    name: str  # e.g. MyClass.cls, MyTrigger.trigger
    link: str  # e.g. MyClass.cls_orgpmd.html
    git_log: str = ""
    issues: List[Issue] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.issues)

    @property
    def high(self) -> int:
        return sum(1 for i in self.issues if i.is_high)


# --------------------------------------------------------------------
# Git helpers
# --------------------------------------------------------------------

def run_git_command(args) -> str:
    try:
        result = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
        out = result.stdout.strip()
        return out or "N/A"
    except Exception:
        return "N/A"


def get_git_branch_name() -> str:
    return run_git_command(["git", "rev-parse", "--abbrev-ref", "HEAD"])


def get_git_log_for_path(src_path: Optional[str]) -> str:
    if not src_path:
        return "N/A"
    return run_git_command(
        ["git", "log", "-1", "--pretty=format:%h | %an | %ad | %s", "--", src_path]
    )


# --------------------------------------------------------------------
# PMD parsing / rules
# --------------------------------------------------------------------

def load_high_patterns(path: str) -> List[str]:
    patterns: List[str] = []
    if not os.path.exists(path):
        return patterns
    with open(path, encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            patterns.append(s)
    return patterns


def derive_display_and_link_for_class(fname: str):
    display = fname
    if fname.endswith(".cls_orgpmd.txt"):
        display = fname[:-len(".cls_orgpmd.txt")] + ".cls"
    elif fname.endswith("_orgpmd.txt"):
        display = fname[:-len("_orgpmd.txt")]
    link = f"{display}_orgpmd.html"
    return display, link


def derive_display_and_link_for_trigger(fname: str):
    display = fname
    if fname.endswith(".trigger_orgpmd.txt"):
        display = fname[:-len(".trigger_orgpmd.txt")] + ".trigger"
    elif fname.endswith("_orgpmd.txt"):
        display = fname[:-len("_orgpmd.txt")]
    link = f"{display}_orgpmd.html"
    return display, link


def parse_issue_line(line: str):
    """
    Return: (pattern_name, message, line_no)
    """
    s = line.rstrip("\n")

    # Common PMD style:
    #   src/classes/Abc.cls:23: RULE_NAME: message
    m = re.match(r"^[^:]+:(\d+)(?::\d+)?:\s*([^:]+):\s*(.*)$", s)
    if m:
        line_str = m.group(1)
        try:
            line_no = int(line_str)
        except ValueError:
            line_no = None
        pattern = m.group(2).strip()
        msg = m.group(3).strip()
        return pattern or "PMD Rule", msg or s, line_no

    # Fallback: RULE: message  or [RULE] message
    m = re.match(r"^\s*\[?([^\]]+)\]?\s*[:-]\s*(.*)$", s)
    if m:
        pattern = m.group(1).strip()
        msg = m.group(2).strip()
        return pattern or "PMD Rule", msg or s, None

    # Last fallback
    return "PMD Issue", s, None


def is_high_issue(line: str, pattern_name: str, high_patterns: List[str]) -> bool:
    target = f"{line} {pattern_name}"
    for hp in high_patterns:
        if hp and hp in target:
            return True
    return False


def collect_items(pmd_dir: str,
                  kind: str,
                  high_patterns: List[str],
                  derive_fn,
                  git_base_dir: str):
    items: List[Item] = []
    seen = set()

    if not os.path.isdir(pmd_dir):
        return items

    for fname in sorted(os.listdir(pmd_dir)):
        if not fname.endswith(".txt"):
            continue

        full_path = os.path.join(pmd_dir, fname)
        display, link = derive_fn(fname)
        if not display or display in seen:
            continue
        seen.add(display)

        issues: List[Issue] = []
        with open(full_path, encoding="utf-8", errors="replace") as f:
            for line in f:
                if not line.strip():
                    continue
                pattern_name, msg, line_no = parse_issue_line(line)
                high = is_high_issue(line, pattern_name, high_patterns)
                issues.append(
                    Issue(
                        pattern=pattern_name,
                        message=msg,
                        line_no=line_no,
                        is_high=high,
                    )
                )

        # Map from display name to real git path:
        #   Class:   src/classes/<Name>.cls
        #   Trigger: src/triggers/<Name>.trigger
        git_path = os.path.join(git_base_dir, display) if git_base_dir else None
        git_log = get_git_log_for_path(git_path)

        items.append(
            Item(
                kind=kind,
                name=display,
                link=link,
                git_log=git_log,
                issues=issues,
            )
        )

    return items


# --------------------------------------------------------------------
# HTML helpers
# --------------------------------------------------------------------

def html_escape(s: str) -> str:
    return html.escape(s, quote=True)


def truncate(s: str, max_len: int = 100) -> str:
    if len(s) <= max_len:
        return s
    return s[: max_len - 1] + "…"


# --------------------------------------------------------------------
# INDEX HTML
# --------------------------------------------------------------------

def build_index_html(env: str,
                     branch: str,
                     now_str: str,
                     classes: List[Item],
                     triggers: List[Item],
                     output_path: str):
    classes_rows = []
    triggers_rows = []

    for item in classes:
        css_class = "sev-none"
        if item.total > 0 and item.high == 0:
            css_class = "sev-warn"
        if item.high > 0:
            css_class = "sev-high"
        git_short = truncate(item.git_log, 80)
        classes_rows.append(
            f'<tr data-total="{item.total}" data-high="{item.high}">'
            f'<td class="name"><a href="{html_escape(item.link)}" '
            f'class="{css_class}">{html_escape(item.name)}</a></td>'
            f'<td class="git" title="{html_escape(item.git_log)}">'
            f'{html_escape(git_short)}</td>'
            f'<td class="num">{item.total}({item.high})</td>'
            f'</tr>'
        )

    for item in triggers:
        css_class = "sev-none"
        if item.total > 0 and item.high == 0:
            css_class = "sev-warn"
        if item.high > 0:
            css_class = "sev-high"
        git_short = truncate(item.git_log, 80)
        triggers_rows.append(
            f'<tr data-total="{item.total}" data-high="{item.high}">'
            f'<td class="name"><a href="{html_escape(item.link)}" '
            f'class="{css_class}">{html_escape(item.name)}</a></td>'
            f'<td class="git" title="{html_escape(item.git_log)}">'
            f'{html_escape(git_short)}</td>'
            f'<td class="num">{item.total}({item.high})</td>'
            f'</tr>'
        )

    classes_total = len(classes)
    triggers_total = len(triggers)
    all_issues = sum(it.total for it in classes + triggers)
    all_high = sum(it.high for it in classes + triggers)

    classes_rows_html = "\n".join(classes_rows)
    triggers_rows_html = "\n".join(triggers_rows)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Original Combined PMD Report</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  :root {{
    --bg:#0f172a; --card:#0b1220; --ink:#e5e7eb; --ink-d:#a1a1aa;
    --line:#1f2937; --accent:#4f46e5; --accent2:#06b6d4;
    --good:#22c55e; --warn:#facc15; --high:#f97373;
  }}
  html,body {{
    margin:0; padding:0; background:#020617; color:var(--ink);
    font:14px/1.6 system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Cantarell,"Helvetica Neue",Arial,"Noto Sans",sans-serif;
  }}
  .wrap {{ max-width:1100px; margin:0 auto; padding:24px; }}

  header {{
    position: sticky; top:0; z-index:40;
    background:linear-gradient(180deg,#020617,#020617f2 60%,#020617d0);
    backdrop-filter:blur(18px);
    border-bottom:1px solid var(--line);
    padding:18px 0 14px;
  }}
  .title {{
    font-size:26px; font-weight:800; letter-spacing:.2px; margin:0 0 4px 0;
    background:linear-gradient(90deg,#fff,#c7d2fe,#99f6e4);
    -webkit-background-clip:text; background-clip:text; color:transparent;
  }}
  .meta {{ color:var(--ink-d); font-size:12px; }}
  .toolbar {{
    margin-top:10px; display:flex; flex-wrap:wrap;
    gap:10px; align-items:center;
  }}
  .btn {{
    display:inline-block; padding:8px 14px; border-radius:999px; border:0;
    background:linear-gradient(180deg,#8b5cf6,#4f46e5 60%,#0ea5e9);
    color:#fff; text-decoration:none; font-weight:700; letter-spacing:.2px;
    box-shadow:0 10px 18px rgba(79,70,229,.35), inset 0 1px 0 rgba(255,255,255,.35);
    transition:transform .12s ease, filter .12s ease;
    font-size:13px;
  }}
  .btn:hover {{ transform:translateY(-1px); filter:brightness(1.05); }}
  .btn-sm {{ padding:6px 10px; font-size:11px; }}

  .spacer {{ flex:1 1 auto; }}

  .search-wrap input {{
    background:#020617; border:1px solid #1e293b; border-radius:999px;
    padding:6px 12px; font-size:13px; color:var(--ink);
    min-width:180px;
  }}
  .search-wrap input:focus {{
    outline:none; border-color:var(--accent2); box-shadow:0 0 0 1px rgba(56,189,248,.3);
  }}

  .filters {{
    margin-top:14px; display:flex; gap:8px; flex-wrap:wrap;
  }}
  .chip {{
    border-radius:999px; padding:4px 10px; font-size:11px;
    border:1px solid #1e293b; background:#020617; color:var(--ink-d);
    cursor:pointer;
  }}
  .chip-active {{
    border-color:var(--accent2);
    background:radial-gradient(circle at top,#0f172a,#020617);
    color:#e5e7eb;
  }}

  .legend {{
    margin-top:18px;
  }}
  .legend-card {{
    background:radial-gradient(circle at top left,#0b1120,#020617);
    border-radius:16px;
    border:1px solid #1f2937;
    padding:14px 16px;
    box-shadow:0 6px 18px rgba(0,0,0,.45);
  }}
  .legend-card h2 {{
    font-size:14px; margin:0 0 8px 0; text-transform:uppercase; letter-spacing:.12em;
    color:#e5e7eb;
  }}
  .legend-body {{ font-size:12px; color:var(--ink-d); }}
  .legend-body code {{ background:#020617; padding:1px 4px; border-radius:4px; }}
  .legend-grid {{
    margin-top:8px; display:flex; flex-wrap:wrap; gap:10px 24px; font-size:12px;
  }}
  .legend-grid .row {{ display:flex; align-items:center; gap:6px; }}
  .dot {{
    width:8px; height:8px; border-radius:999px;
    display:inline-block;
  }}
  .dot-high {{ background:var(--high); }}
  .dot-warn {{ background:var(--warn); }}
  .dot-normal {{ background:#64748b; }}
  .legend-stats {{
    margin-top:10px; font-size:12px; display:flex; gap:12px; flex-wrap:wrap;
  }}

  .grid {{
    margin-top:20px; display:grid;
    grid-template-columns:repeat(2,minmax(0,1fr)); gap:18px;
  }}
  @media (max-width:900px) {{
    .grid {{ grid-template-columns:1fr; }}
  }}

  .card {{
    background:linear-gradient(180deg,#020617,#020617);
    border:1px solid var(--line);
    border-radius:16px; overflow:hidden;
    box-shadow:0 6px 24px rgba(0,0,0,.4);
  }}
  .card-head {{
    display:flex; justify-content:space-between; align-items:center;
    padding:12px 14px; border-bottom:1px solid var(--line); background:#020617;
  }}
  .card-head h2 {{ font-size:15px; margin:0; }}
  .pill {{
    display:inline-block; margin-left:8px; padding:1px 8px; font-size:11px;
    border-radius:999px; background:#0b2b1a; color:#86efac; border:1px solid #14532d;
  }}

  table {{ width:100%; border-collapse:collapse; }}
  thead th {{
    position:sticky; top:0;
    text-align:left; font-weight:700; color:#cbd5e1; font-size:11px;
    letter-spacing:.16em; text-transform:uppercase;
    padding:8px 10px; background:#020617; border-bottom:1px solid var(--line);
    z-index:10;
  }}
  tbody td {{
    padding:8px 10px; border-bottom:1px dashed #1b2437; vertical-align:middle;
  }}
  tbody tr:hover {{ background:rgba(79,70,229,.08); }}
  td.name a {{
    color:#e5e7eb; text-decoration:none; font-weight:600;
  }}
  td.name a:hover {{ text-decoration:underline; }}
  td.name a.sev-warn {{ color:var(--warn); }}
  td.name a.sev-high {{ color:var(--high); }}
  td.git {{
    font-size:11px; color:var(--ink-d);
  }}
  td.num {{ text-align:right; font-variant-numeric:tabular-nums; }}

  footer {{
    margin-top:24px; background:#000; color:#fff;
    padding:14px 16px; text-align:center; border-top:1px solid #111;
    font-size:11px;
  }}
  .end {{ opacity:.9; font-weight:700; letter-spacing:.3px; }}
</style>
</head>
<body>
  <div class="wrap">
    <header>
      <div class="title">Original Combined PMD Report</div>
      <div class="meta">
        Environment: <strong>{html_escape(env)}</strong>
        &nbsp;&bull;&nbsp;
        Branch: <strong>{html_escape(branch)}</strong>
        &nbsp;&bull;&nbsp;
        Generated: {html_escape(now_str)}
      </div>
      <div class="toolbar">
        <a class="btn" href="Original_Combined_PMD_Report.csv" download>
          Download Combined CSV
        </a>
        <div class="spacer"></div>
        <div class="search-wrap">
          <input id="searchInput" type="search" placeholder="Search class/trigger...">
        </div>
      </div>
      <div class="filters">
        <button class="chip chip-active" data-filter="all">All</button>
        <button class="chip" data-filter="high">With High</button>
        <button class="chip" data-filter="nohigh">No High</button>
      </div>
    </header>

    <section class="legend">
      <div class="legend-card">
        <h2>Legend &amp; Totals</h2>
        <div class="legend-body">
          Issues column shows <strong>Total(High)</strong>.
          Example: <code>36(3)</code> means 36 total PMD issues, of which 3 are high-severity.
          Severity: <strong>High</strong> if it matches any pattern from <code>pmd_high_patterns.txt</code>, otherwise <strong>Low</strong>.
        </div>
        <div class="legend-grid">
          <div class="row">
            <span class="dot dot-high"></span>
            <span>Red name: file has at least one HIGH pattern.</span>
          </div>
          <div class="row">
            <span class="dot dot-warn"></span>
            <span>Orange name: file has PMD issues but no HIGH pattern.</span>
          </div>
          <div class="row">
            <span class="dot dot-normal"></span>
            <span>Default name: no issues (if listed).</span>
          </div>
        </div>
        <div class="legend-stats">
          <div>Classes: <strong>{classes_total}</strong></div>
          <div>Triggers: <strong>{triggers_total}</strong></div>
          <div>All issues: <strong>{all_issues}({all_high})</strong></div>
        </div>
      </div>
    </section>

    <section class="grid">
      <div class="card">
        <div class="card-head">
          <h2>Classes <span class="pill">{classes_total}</span></h2>
          <a class="btn btn-sm" href="Original_Combined_PMD_Report_Classes.csv" download>
            Download Classes CSV
          </a>
        </div>
        <table>
          <thead><tr><th>Name</th><th>Git Author Log (last)</th><th style="text-align:right">PMD Issues</th></tr></thead>
          <tbody>
{classes_rows_html}
          </tbody>
        </table>
      </div>

      <div class="card">
        <div class="card-head">
          <h2>Triggers <span class="pill">{triggers_total}</span></h2>
          <a class="btn btn-sm" href="Original_Combined_PMD_Report_Triggers.csv" download>
            Download Triggers CSV
          </a>
        </div>
        <table>
          <thead><tr><th>Name</th><th>Git Author Log (last)</th><th style="text-align:right">PMD Issues</th></tr></thead>
          <tbody>
{triggers_rows_html}
          </tbody>
        </table>
      </div>
    </section>

    <footer><div class="end">End of the Report.</div></footer>
  </div>

<script>
(function() {{
  const searchInput = document.getElementById('searchInput');
  const filterButtons = document.querySelectorAll('[data-filter]');
  const rows = Array.from(document.querySelectorAll('tbody tr'));
  let activeFilter = 'all';
  let searchTerm = '';

  function applyFilters() {{
    const term = searchTerm.toLowerCase();
    rows.forEach(row => {{
      const nameCell = row.querySelector('.name');
      if (!nameCell) return;
      const name = nameCell.textContent.toLowerCase();
      const total = parseInt(row.dataset.total || '0', 10);
      const high = parseInt(row.dataset.high || '0', 10);

      let matchSearch = !term || name.includes(term);
      let matchFilter = true;

      if (activeFilter === 'high') {{
        matchFilter = high > 0;
      }} else if (activeFilter === 'nohigh') {{
        matchFilter = (total > 0 && high === 0);
      }}

      row.style.display = (matchSearch && matchFilter) ? '' : 'none';
    }});
  }}

  if (searchInput) {{
    searchInput.addEventListener('input', e => {{
      searchTerm = e.target.value || '';
      applyFilters();
    }});
  }}

  filterButtons.forEach(btn => {{
    btn.addEventListener('click', () => {{
      filterButtons.forEach(b => b.classList.remove('chip-active'));
      btn.classList.add('chip-active');
      activeFilter = btn.dataset.filter || 'all';
      applyFilters();
    }});
  }});
}})();
</script>

</body>
</html>
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)


# --------------------------------------------------------------------
# DETAIL HTML
# --------------------------------------------------------------------

def build_detail_html(item: Item,
                      env: str,
                      branch: str,
                      now_str: str,
                      output_dir: str):
    rows_html = []
    for idx, issue in enumerate(item.issues, start=1):
        row_cls = "row-high" if issue.is_high else ""
        severity = "High" if issue.is_high else "Low"
        line_display = str(issue.line_no) if issue.line_no is not None else "-"
        rows_html.append(
            f'<tr class="{row_cls}">'
            f'<td class="idx">{idx}</td>'
            f'<td class="line">{html_escape(line_display)}</td>'
            f'<td class="pattern">{html_escape(issue.pattern)}</td>'
            f'<td class="msg">{html_escape(issue.message)}</td>'
            f'<td class="sev">{severity}</td>'
            f'</tr>'
        )

    rows_html_str = "\n".join(rows_html)
    high_class = "score-high" if item.high > 0 else "score-normal"

    content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{html_escape(item.name)} - PMD Issues</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  :root {{
    --bg:#020617; --card:#020617; --ink:#e5e7eb; --ink-d:#a1a1aa;
    --line:#1f2937; --high:#f97373; --warn:#facc15;
  }}
  html,body {{
    margin:0; padding:0; background:var(--bg); color:var(--ink);
    font:14px/1.6 system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Cantarell,"Helvetica Neue",Arial,"Noto Sans",sans-serif;
  }}
  .wrap {{ max-width:960px; margin:0 auto; padding:20px; }}
  header {{ border-bottom:1px solid var(--line); padding-bottom:10px; margin-bottom:12px; }}
  .crumbs a {{ color:#93c5fd; font-size:12px; text-decoration:none; }}
  .crumbs a:hover {{ text-decoration:underline; }}
  .name {{
    font-size:20px; font-weight:700; margin:6px 0 2px 0;
  }}
  .meta {{ font-size:12px; color:var(--ink-d); }}
  .git-meta {{
    font-size:11px; color:var(--ink-d); margin-top:4px;
  }}
  .score {{
    margin-top:8px; font-size:13px;
  }}
  .score span {{ margin-right:10px; }}
  .score-high {{ color:var(--high); font-weight:700; }}
  .score-normal {{ color:#22c55e; }}
  table {{ width:100%; border-collapse:collapse; margin-top:16px; }}
  thead th {{
    text-align:left; font-size:11px; text-transform:uppercase;
    letter-spacing:.16em; color:#cbd5e1;
    padding:8px 8px; border-bottom:1px solid var(--line);
  }}
  tbody td {{
    padding:8px 8px; border-bottom:1px dashed #1f2937;
    vertical-align:top;
  }}
  tbody tr:hover {{ background:rgba(148,163,184,.14); }}
  .idx {{ width:40px; text-align:right; font-variant-numeric:tabular-nums; }}
  .line {{ width:60px; text-align:right; font-variant-numeric:tabular-nums; }}
  .pattern {{ width:220px; font-weight:600; font-size:13px; }}
  .msg {{ font-size:13px; }}
  .sev {{ width:70px; font-size:12px; }}
  .row-high td {{ color:var(--high); }}
  footer {{
    margin-top:18px; padding-top:10px; border-top:1px solid #111;
    font-size:11px; color:var(--ink-d); text-align:center;
  }}
</style>
</head>
<body>
  <div class="wrap">
    <header>
      <div class="crumbs"><a href="index.html">&larr; Back to Combined PMD Report</a></div>
      <div class="name">{html_escape(item.name)}</div>
      <div class="meta">
        {html_escape(item.kind)} &nbsp;&bull;&nbsp;
        Environment: <strong>{html_escape(env)}</strong> &nbsp;&bull;&nbsp;
        Branch: <strong>{html_escape(branch)}</strong> &nbsp;&bull;&nbsp;
        Generated: {html_escape(now_str)}
      </div>
      <div class="git-meta">
        Git Author Log (last): {html_escape(item.git_log)}
      </div>
      <div class="score">
        <span>Total issues: <strong>{item.total}</strong></span>
        <span class="{high_class}">High issues: <strong>{item.high}</strong></span>
      </div>
    </header>

    <section>
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>Line</th>
            <th>Pattern Name</th>
            <th>Issue</th>
            <th>Severity</th>
          </tr>
        </thead>
        <tbody>
{rows_html_str}
        </tbody>
      </table>
    </section>

    <footer>End of PMD detail report.</footer>
  </div>
</body>
</html>
"""
    out_path = os.path.join(output_dir, item.link)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)


# --------------------------------------------------------------------
# CSVs
# --------------------------------------------------------------------

def write_csvs(output_dir: str, classes: List[Item], triggers: List[Item]):
    combined_path = os.path.join(output_dir, "Original_Combined_PMD_Report.csv")
    classes_path = os.path.join(output_dir, "Original_Combined_PMD_Report_Classes.csv")
    triggers_path = os.path.join(output_dir, "Original_Combined_PMD_Report_Triggers.csv")

    # Combined summary – one row per class/trigger
    with open(combined_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Type", "Name", "Total_Issues", "High_Issues", "Link", "Git_Author_Log"])
        for item in classes + triggers:
            w.writerow([item.kind, item.name, item.total, item.high, item.link, item.git_log])

    # Detailed classes – one row per issue
    with open(classes_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Type", "Name", "Line", "Pattern", "Issue", "Severity", "Git_Author_Log"])
        for item in classes:
            for iss in item.issues:
                severity = "High" if iss.is_high else "Low"
                line_val = iss.line_no if iss.line_no is not None else ""
                w.writerow([item.kind, item.name, line_val, iss.pattern, iss.message, severity, item.git_log])

    # Detailed triggers
    with open(triggers_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Type", "Name", "Line", "Pattern", "Issue", "Severity", "Git_Author_Log"])
        for item in triggers:
            for iss in item.issues:
                severity = "High" if iss.is_high else "Low"
                line_val = iss.line_no if iss.line_no is not None else ""
                w.writerow([item.kind, item.name, line_val, iss.pattern, iss.message, severity, item.git_log])

    print(f"✔ Wrote: {combined_path}")
    print(f"✔ Wrote: {classes_path}")
    print(f"✔ Wrote: {triggers_path}")


# --------------------------------------------------------------------
# Main
# --------------------------------------------------------------------

def main():
    # Same semantics as your bash: ENV is required
    if len(sys.argv) < 2:
        prog = os.path.basename(sys.argv[0] or "generate_pmd_original_report.py")
        print(f"Usage: {prog} <ENV>")
        sys.exit(1)

    env = sys.argv[1]
    output_dir = os.path.join(OUTPUT_ROOT, env)
    os.makedirs(output_dir, exist_ok=True)

    # Clean previous HTML/CSV (keep other artifacts)
    for name in os.listdir(output_dir):
        full = os.path.join(output_dir, name)
        if name.endswith(".csv"):
            os.remove(full)
        elif name.endswith(".html") and name != "index.html":
            os.remove(full)

    high_patterns = load_high_patterns(PMD_HIGH_PATTERNS_FILE)
    print(f"Loaded {len(high_patterns)} high patterns from {PMD_HIGH_PATTERNS_FILE}")

    classes = collect_items(PMD_CLASSES_DIR, "Class", high_patterns,
                            derive_display_and_link_for_class, GIT_CLASSES_DIR)
    triggers = collect_items(PMD_TRIGGERS_DIR, "Trigger", high_patterns,
                             derive_display_and_link_for_trigger, GIT_TRIGGERS_DIR)

    classes.sort(key=lambda i: i.name.lower())
    triggers.sort(key=lambda i: i.name.lower())

    now = datetime.now(timezone.utc).astimezone()
    now_str = now.strftime("%d %b %Y, %I:%M %p %Z")
    branch = get_git_branch_name()

    write_csvs(output_dir, classes, triggers)

    for item in classes + triggers:
        build_detail_html(item, env, branch, now_str, output_dir)

    index_path = os.path.join(output_dir, "index.html")
    build_index_html(env, branch, now_str, classes, triggers, index_path)

    print(f"✔ Wrote: {index_path}")
    print(f"✔ Detail HTML written under: {output_dir}")


if __name__ == "__main__":
    main()
