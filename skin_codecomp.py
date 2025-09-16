#!/usr/bin/env python3
from pathlib import Path
import argparse
import re
import sys

CSS = r"""
<style id="skin-codecomp">
/* main title a touch smaller so it fits one line */
.h-title h1{font-size:clamp(16px,2vw,22px);font-weight:900;letter-spacing:.2px}

/* compact, left-aligned table; clearer header */
main table.summary{width:auto;margin:0;border-collapse:separate;border-spacing:0 8px}
main table.summary thead th{
  background:#f1f5f9;color:#0f172a;font-weight:900;
  border:1px solid #e6e9ef;border-bottom-color:#dbe4ef;
  text-align:left;padding:10px 12px;white-space:nowrap
}
main table.summary thead th:first-child{border-top-left-radius:12px;border-bottom-left-radius:12px}
main table.summary thead th:last-child {border-top-right-radius:12px;border-bottom-right-radius:12px}
main table.summary tbody td{
  border-top:1px solid #e6e9ef;border-bottom:1px solid #e6e9ef;
  text-align:left;padding:10px 12px;white-space:nowrap
}
main table.summary tbody tr td:first-child{border-left:1px solid #e6e9ef;border-top-left-radius:12px;border-bottom-left-radius:12px}
main table.summary tbody tr td:last-child {border-right:1px solid #e6e9ef;border-top-right-radius:12px;border-bottom-right-radius:12px}

/* keep existing palette */
.num.black{color:#111}.num.green{color:#16a34a}.num.orange{color:#d97706}
</style>
"""

DATE_DIR_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

def inject_skin(page: Path) -> bool:
    if not page.exists():
        print(f"skip: not found -> {page}")
        return False
    html = page.read_text(encoding="utf-8")
    if 'id="skin-codecomp"' in html:
        print(f"ok: already styled -> {page}")
        return False
    if "</head>" not in html:
        print(f"err: cannot find </head> in -> {page}")
        return False
    page.write_text(html.replace("</head>", CSS + "\n</head>"), encoding="utf-8")
    print(f"ok: injected -> {page}")
    return True

def latest_run_dir(root: Path) -> Path | None:
    if not root.exists():
        return None
    dirs = [d for d in root.iterdir() if d.is_dir() and DATE_DIR_RE.match(d.name)]
    if not dirs:
        return None
    # sort by name (YYYY-MM-DD) -> lexicographic is chronological
    return sorted(dirs, key=lambda p: p.name)[-1]

def codecomp_for_run(run_dir: Path) -> Path:
    return run_dir / "codecomp.html"

def all_runs(root: Path):
    for d in sorted([p for p in root.iterdir() if p.is_dir() and DATE_DIR_RE.match(p.name)]):
        yield d

def main():
    ap = argparse.ArgumentParser(description="Post-skin codecomp.html (no code changes needed).")
    ap.add_argument("path", nargs="?", help="Path to a specific codecomp.html (optional).")
    ap.add_argument("--root", default="/data/public/ProdvsProdComp",
                    help="Root containing YYYY-MM-DD run folders (default: %(default)s)")
    ap.add_argument("--all", action="store_true",
                    help="Inject styles into every run under --root")
    args = ap.parse_args()

    root = Path(args.root)

    # 1) If a specific file path was given, use it.
    if args.path:
        target = Path(args.path)
        if target.is_dir():
            target = target / "codecomp.html"
        inject_skin(target)
        return

    # 2) If --all: style all runs under root.
    if args.all:
        any_found = False
        for run in all_runs(root):
            any_found = True
            inject_skin(codecomp_for_run(run))
        if not any_found:
            print(f"no runs found under {root}")
        return

    # 3) No args: try CWD/codecomp.html, else latest run under root.
    cwd_target = Path.cwd() / "codecomp.html"
    if cwd_target.exists():
        inject_skin(cwd_target)
        return

    run = latest_run_dir(root)
    if not run:
        print(f"no date folders under {root}; pass a path or fix --root")
        sys.exit(1)
    inject_skin(codecomp_for_run(run))

if __name__ == "__main__":
    main()
