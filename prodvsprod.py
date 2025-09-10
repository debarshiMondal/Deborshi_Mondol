#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SFDC Production Metadata Dump Comparison – end-to-end builder

Changes in this version:
- Detail page: button-like section tabs, Back button, larger logo, KPI labels bold, Diff section before Types.
- Full report now saved as XLSX: ProdDumpComparison_List_{EXEC_DATE}.xlsx (no "(Execution Date)").
  Adds new column "DevOps Team Comment" after "PS team Comment".
  Falls back to CSV if openpyxl is not present; link adapts to actual extension.
- Sends a success email with Master & Detailed links (needs [links] public_base_url in setup.conf).
- Auto-updates lastdumpcomp.date to the latest dump name after successful run.
- Keeps all previous features (searchable master, SharePoint link pattern, required metadata, etc.).

Additional changes (this commit):
- Provide PREVIOUS_DATE_HUMAN, LATEST_DATE_HUMAN, PREVIOUS_DATE_DASH, LATEST_DATE_DASH for the detail template.
- Produce changed_files_only.xlsx (XLSX only). If XLSX write fails or openpyxl missing, send error email and exit with error.
- Expose CSV_CHANGED -> "./changed_files_only.xlsx" to the template.
"""

import os
import re
import csv
import sys
import json
import shutil
import hashlib
import subprocess
import datetime as dt
from collections import Counter
from configparser import ConfigParser
from pathlib import Path
from email.mime_text import MIMEText
import smtplib

# ---------- utils ----------
def load_conf(p: Path) -> ConfigParser:
    if not p.exists():
        sys.exit(f"[ERROR] Missing config: {p}")
    # Allow % in URLs (e.g., %20)
    c = ConfigParser(interpolation=None)
    c.read(p)
    return c

def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8") if p.exists() else ""

def write_text(p: Path, s: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8")

def append_text(p: Path, s: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(s)

def copy_tree(src: Path, dst: Path):
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)

def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for ch in iter(lambda: f.read(1024 * 1024), b""):
            h.update(ch)
    return h.hexdigest()

def find_latest_dump(root: Path) -> Path:
    c = [p for p in root.iterdir() if p.is_dir()]
    if not c:
        sys.exit(f"[ERROR] No dumps under {root}")
    c.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return c[0]

def top_level_dirs(p: Path) -> set:
    return {x.name for x in p.iterdir() if x.is_dir()}

def walk_files(base: Path):
    for r, _, fs in os.walk(base):
        for f in fs:
            full = Path(r) / f
            yield full.relative_to(base), full

def today_iso() -> str:
    return dt.date.today().isoformat()

def sync_assets(src: Path, dst: Path):
    """Deploy assets from script's assets/ to the public web assets/."""
    if not src.exists():
        return
    dst.mkdir(parents=True, exist_ok=True
    )
    for p in src.iterdir():
        if p.is_file():
            shutil.copy2(p, dst / p.name)

# ---------- date helpers ----------
DATE_TOKEN_RE = re.compile(r'(\d{1,2})(?:st|nd|rd|th)?([A-Za-z]+)(\d{4})')
MONTH_ABBR_FOR_EXEC = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",7:"Jul",8:"Aug",9:"Sept",10:"Oct",11:"Nov",12:"Dec"}
MONTH_LONG = {1:"January",2:"February",3:"March",4:"April",5:"May",6:"June",7:"July",8:"August",9:"September",10:"October",11:"November",12:"December"}

def parse_dump_date_token(name: str):
    m = DATE_TOKEN_RE.search(name)
    if not m:
        return None
    day = int(m.group(1))
    mon_token = m.group(2).lower()
    year = int(m.group(3))
    table = [ "jan","feb","mar","apr","may","jun","jul","aug","sept","oct","nov","dec" ]
    month = None
    for key in ("sept","sep","jan","feb","mar","apr","may","jun","jul","aug","oct","nov","dec"):
        if mon_token.startswith(key):
            month = table.index("sept" if key == "sept" else key) + 1
            break
    if not month:
        return None
    try:
        return dt.date(year, month, day)
    except ValueError:
        return None

def ordinal(n: int) -> str:
    return f"{n}{'th' if 11<=n%100<=13 else {1:'st',2:'nd',3:'rd'}.get(n%10,'th')}"

def display_long(d: dt.date) -> str:
    return f"{ordinal(d.day)} {MONTH_LONG[d.month]} {d.year}"

# >>> ADDED: dashed date format for buttons
def display_dash(d: dt.date) -> str:
    return f"{d.day:02d}-{d.month:02d}-{d.year}"

def exec_date_token(d: dt.date) -> str:
    """Return token like '7Sept2025' for the file name."""
    return f"{d.day}{MONTH_ABBR_FOR_EXEC[d.month]}{d.year}"

# ---------- email ----------
def send_mail(cfg: ConfigParser, subj: str, body: str):
    rcpts = [x.strip() for x in cfg.get("mail", "to", fallback="").split(",") if x.strip()]
    if not rcpts:
        return
    method = cfg.get("mail", "method", fallback="mutt").strip().lower()
    try:
        if method == "mutt":
            subprocess.run(["mutt", "-s", subj, *rcpts], input=body.encode(), check=False)
        elif method == "sendmail":
            msg = f"Subject: {subj}\nTo: {', '.join(rcpts)}\n\n{body}"
            subprocess.run(["/usr/sbin/sendmail", "-t", "-oi"], input=msg.encode(), check=False)
        else:
            host = cfg.get("smtp", "host")
            port = cfg.getint("smtp", "port", fallback=587)
            user = cfg.get("smtp", "user", fallback="")
            pwd  = cfg.get("smtp", "password", fallback="")
            sender = cfg.get("smtp", "from", fallback=user or "noreply@example.com")
            use_tls = cfg.getboolean("smtp", "starttls", fallback=True)
            msg = MIMEText(body, "plain", "utf-8")
            msg["Subject"] = subj
            msg["From"] = sender
            msg["To"] = ", ".join(rcpts)
            with smtplib.SMTP(host, port, timeout=45) as s:
                s.ehlo()
                if use_tls:
                    s.starttls()
                    s.ehlo()
                if user:
                    s.login(user, pwd)
                s.sendmail(sender, rcpts, msg.as_string())
    except Exception as e:
        print(f"[WARN] mail failed: {e}", file=sys.stderr)

# ---------- html helpers ----------
def counts_to_html(counter: Counter) -> str:
    if not counter:
        return '<div class="note">N/A</div>'
    items = []
    for t, n in sorted(counter.items(), key=lambda kv: (-kv[1], kv[0].lower())):
        items.append(f'<li><span class="t">{t}</span><span class="c">{n}</span></li>')
    return '<ul class="typecounts">' + "".join(items) + '</ul>'

def chips_html(items) -> str:
    return ('<div class="chips">' + "".join(f'<span class="chip meta">{x}</span>' for x in items) + '</div>') if items else '<div class="note">No metadata configured.</div>'

def render_template(tpl: str, **kw) -> str:
    out = tpl
    for k, v in kw.items():
        out = out.replace("{{" + k + "}}", str(v))
    return out

def inject_master(tpl: str, reports: list, logo_rel: str, meta_html: str) -> str:
    js = json.dumps(reports, ensure_ascii=False).replace("</script>", "<\\/script>")
    return tpl.replace("{{REPORT_CARDS_JSON}}", js)\
              .replace("{{CADENCE_LOGO}}", logo_rel)\
              .replace("{{METADATA_SIDEBAR_HTML}}", meta_html)

# ---------- main ----------
def main():
    here = Path(__file__).resolve().parent
    cfg  = load_conf(here / "setup.conf")

    P = {
        "dumps":  Path(cfg.get("paths", "dumps_root",        fallback="/backup/PROD_DUMP")),
        "work":   Path(cfg.get("paths", "work_root",         fallback="/data/public/ProdvsProdComp")),
        "script": Path(cfg.get("paths", "compare_script_dir",fallback="/softwere/codedev/misc_script/SFDC/BCompareScript")),
        "last":   Path(cfg.get("paths", "lastdump_file",     fallback=str(here / "lastdumpcomp.date"))),
        "tpl":    Path(cfg.get("paths", "templates_dir",     fallback=str(here / "templates"))),
        "assets": Path(cfg.get("paths", "assets_dir",        fallback=str(here / "assets"))),
    }

    # Deploy assets (logo) to web root
    public_assets = P["work"] / "assets"
    sync_assets(P["assets"], public_assets)
    logo_master_rel = "assets/cadence-logo.png"     # from /ProdvsProdComp/index.html
    logo_detail_rel = "../assets/cadence-logo.png"  # from /ProdvsProdComp/YYYY-MM-DD/index.html

    # Required metadata folders (top-level)
    req_raw = cfg.get("metadata", "current_sfdc_metadata_list_used_in_cadence", fallback="")
    req = [x.strip() for x in req_raw.split(",") if x.strip()]

    # Resolve dumps
    old_name = read_text(P["last"]).strip()
    if not old_name:
        send_mail(cfg, "[ProdvsProd] lastdumpcomp.date is empty", f"Populate {P['last']} with the PREVIOUS dump folder name.")
        sys.exit(1)
    old_src = P["dumps"] / old_name
    if not old_src.exists():
        send_mail(cfg, "[ProdvsProd] previous dump missing", f"Not found: {old_src}")
        sys.exit(1)
    new_src = find_latest_dump(P["dumps"])

    # API version
    m = re.search(r"prod_([0-9.]+)_", new_src.name)
    api = m.group(1) if m else cfg.get("ui", "api_version_fallback", fallback="62.0")

    # Friendly title for master & detail
    def title_from_names(o: str, n: str) -> str:
        d_old = parse_dump_date_token(o)
        d_new = parse_dump_date_token(n)
        if d_old and d_new:
            return f"Production Dump Comparison: {display_long(d_old)} vs. {display_long(d_new)}"
        return f"Production Dump Comparison: {o} vs. {n}"
    title = title_from_names(old_src.name, new_src.name)

    # >>> ADDED: derive human/dash dates for template
    d_old = parse_dump_date_token(old_src.name)
    d_new = parse_dump_date_token(new_src.name)
    prev_human = display_long(d_old) if d_old else old_src.name
    latest_human = display_long(d_new) if d_new else new_src.name
    prev_dash = display_dash(d_old) if d_old else ""
    latest_dash = display_dash(d_new) if d_new else ""

    # Prepare run folder
    day = today_iso()
    run = P["work"] / day
    run.mkdir(parents=True, exist_ok=True)
    log = run / "run.log"
    write_text(log, f"[{dt.datetime.now().isoformat(timespec='seconds')}] Run start\nOld: {old_src}\nNew: {new_src}\n\n")

    # Copy dumps into run folder
    prev_dir = run / old_src.name
    latest_dir = run / new_src.name
    copy_tree(old_src, prev_dir);   append_text(log, f"Copied -> {prev_dir}\n")
    copy_tree(new_src, latest_dir); append_text(log, f"Copied -> {latest_dir}\n")

    # Parity & required metadata
    tl_prev = top_level_dirs(prev_dir)
    tl_new  = top_level_dirs(latest_dir)
    if tl_prev != tl_new:
        msg = (f"Top-level folder mismatch.\nPrev: {sorted(tl_prev)}\nLatest: {sorted(tl_new)}\nRun: {run}")
        append_text(log, "[ERROR] " + msg + "\n")
        send_mail(cfg, "[ProdvsProd] Folder name mismatch", msg)
        sys.exit(2)
    if req:
        miss_prev = [m for m in req if m not in tl_prev]
        miss_new  = [m for m in req if m not in tl_new]
        if miss_prev or miss_new:
            msg = (f"Required metadata missing.\n"
                   f"Required: {req}\n"
                   f"Missing in PREVIOUS ({old_src.name}): {miss_prev}\n"
                   f"Missing in LATEST ({new_src.name}): {miss_new}\nRun: {run}")
            append_text(log, "[ERROR] " + msg + "\n")
            send_mail(cfg, "[ProdvsProd] Required metadata missing in dumps", msg)
            sys.exit(3)

    # component.list for external compare
    write_text(P["script"] / "component.list", "\n".join(sorted(tl_prev)) + "\n")

    # Pre-create compare output dir expected by codecompare script
    comp_dir = run / f"{old_src.name}_vs_{new_src.name}" / "codecomp"
    comp_dir.mkdir(parents=True, exist_ok=True)
    append_text(log, f"Prepared compare output dir: {comp_dir}\n")

    # Optional external compare
    if cfg.getboolean("compare", "run_external_compare", fallback=True):
        sh = P["script"] / "codecompare.posix2.sh"
        if sh.exists():
            cmd = ["bash", str(sh), "-d", "-m", "oo", "-o", old_src.name, "-o", new_src.name]
            append_text(log, f"RUN: {' '.join(cmd)} (cwd={run})\n")
            subprocess.run(cmd, cwd=str(run), check=False)
        else:
            append_text(log, f"[WARN] Missing compare script: {sh}\n")

    # Compute diffs
    prev_files   = {rel: f for rel, f in walk_files(prev_dir)}
    latest_files = {rel: f for rel, f in walk_files(latest_dir)}
    new_rel      = [r for r in latest_files if r not in prev_files]
    removed_rel  = [r for r in prev_files  if r not in latest_files]
    changed_rel  = []
    for r in sorted(set(prev_files) & set(latest_files)):
        a, b = prev_files[r], latest_files[r]
        if a.stat().st_size == b.stat().st_size and sha256(a) == sha256(b):
            continue
        changed_rel.append(r)

    # Folder-wise counts
    def top_folder(rel: Path) -> str:
        return rel.parts[0] if rel.parts else "(root)"
    cnt_new = Counter(top_folder(r) for r in new_rel)
    cnt_chg = Counter(top_folder(r) for r in changed_rel)
    cnt_rm  = Counter(top_folder(r) for r in removed_rel)

    # --- FULL REPORT as XLSX (fallback CSV if openpyxl missing) ---
    exec_date = dt.date.today()
    token     = exec_date_token(exec_date)  # e.g., 7Sept2025
    base_name = f"ProdDumpComparison_List_{token}"
    full_ext  = ".xlsx"
    full_path = run / (base_name + full_ext)

    headers = [
        "File List",
        "File Type",                 # "New File" | "Content Mismatch"
        "Dev Team Comment",
        "PS team Comment",
        "DevOps Team Comment",       # NEW
        "Ticket Number",
        "Ticket Resolution Date",
        "Area (Module)",
        "Details of Change Made",
    ]

    wrote_xlsx = False
    try:
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Comparison"
        ws.append(headers)
        for r in sorted(new_rel):
            ws.append([str(r), "New File", "", "", "", "", "", "", ""])
        for r in sorted(changed_rel):
            ws.append([str(r), "Content Mismatch", "", "", "", "", "", "", ""])
        wb.save(full_path)
        wrote_xlsx = True
        append_text(log, f"XLSX written: {full_path}\n")
    except Exception as e:
        append_text(log, f"[WARN] XLSX write failed ({e}); falling back to CSV.\n")
        full_ext  = ".csv"
        full_path = run / (base_name + full_ext)
        with full_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(headers)
            for r in sorted(new_rel):     w.writerow([str(r), "New File",         "", "", "", "", "", "", ""])
            for r in sorted(changed_rel): w.writerow([str(r), "Content Mismatch", "", "", "", "", "", "", ""])
        append_text(log, f"CSV written: {full_path}\n")

    # >>> ADDED: changed_files_only.xlsx (XLSX ONLY, no fallback)
    changed_xlsx = run / "changed_files_only.xlsx"
    try:
        from openpyxl import Workbook
        wb2 = Workbook()
        ws2 = wb2.active
        ws2.title = "Changed Files"
        ws2.append(["File List"])
        for r in sorted(changed_rel):
            ws2.append([str(r)])
        wb2.save(changed_xlsx)
        append_text(log, f"XLSX written: {changed_xlsx}\n")
    except Exception as e:
        msg = f"Failed to write changed_files_only.xlsx: {e}\nRun: {run}"
        append_text(log, "[ERROR] " + msg + "\n")
        send_mail(cfg, "[ProdvsProd] Cannot create changed_files_only.xlsx", msg)
        sys.exit(6)  # hard fail per requirement

    # Ancillary CSVs (these remain CSV)
    csv_new = run / "new_files_only.csv"
    with csv_new.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["File List"])
        for r in sorted(new_rel): w.writerow([str(r)])
    csv_rm  = run / "removed_files_only.csv"
    with csv_rm.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["File List"])
        for r in sorted(removed_rel): w.writerow([str(r)])

    # Link for the full report (SharePoint or local)
    # Supports both keys for compatibility; you can set either.
    sp_pattern = (
        cfg.get("links", "full_report_sharepoint_pattern", fallback="").strip()
        or cfg.get("links", "csv_full_sharepoint_pattern", fallback="").strip()
    )
    ext = "xlsx" if wrote_xlsx else "csv"
    if sp_pattern:
        # Optional {EXEC_DATE} and {EXT} placeholders
        full_href  = sp_pattern.replace("{EXEC_DATE}", token).replace("{EXT}", ext)
        full_label = "CSV Report Link"  # wording retained
    else:
        full_href  = f"./{base_name}{'.xlsx' if wrote_xlsx else '.csv'}"
        full_label = "CSV Report Link"

    # Render Detailed page
    dtpl = read_text(P["tpl"] / "detail_template.html")
    if not dtpl:
        sys.exit(f"[ERROR] Missing template: {P['tpl'] / 'detail_template.html'}")

    detail_html = render_template(
        dtpl,
        PAGE_TITLE      = title,
        TITLE_HEADING   = title,
        API_VERSION     = api,
        REPORT_DATE     = dt.date.today().isoformat(),
        PREVIOUS_LABEL  = old_src.name,
        LATEST_LABEL    = new_src.name,
        PREVIOUS_LINK   = f"./{old_src.name}/",
        LATEST_LINK     = f"./{new_src.name}/",
        KPI_NEW         = len(new_rel),
        KPI_CHANGED     = len(changed_rel),
        KPI_REMOVED     = len(removed_rel),
        CSV_FULL        = full_href,
        CSV_FULL_LABEL  = full_label,
        CSV_NEW         = "./new_files_only.csv",
        CSV_CHANGED     = "./changed_files_only.xlsx",   # >>> ADDED for template
        CSV_REMOVED     = "./removed_files_only.csv",
        DIFF_HTML_LINK  = "./codecomp.html",
        TYPE_COUNTS_NEW = counts_to_html(cnt_new),
        TYPE_COUNTS_CHANGED = counts_to_html(cnt_chg),
        TYPE_COUNTS_REMOVED = counts_to_html(cnt_rm),
        RUN_LOG_LINK    = "./run.log",
        LOGO_HREF       = "../assets/cadence-logo.png",
        # >>> ADDED: date strings for Summary + Quick Access
        PREVIOUS_DATE_HUMAN = prev_human,
        LATEST_DATE_HUMAN   = latest_human,
        PREVIOUS_DATE_DASH  = prev_dash,
        LATEST_DATE_DASH    = latest_dash,
    )
    write_text(run / "index.html", detail_html)

    # Update master database
    db = P["work"] / "reports.json"
    try:
        existing = json.loads(read_text(db)) if db.exists() else []
    except Exception:
        existing = []

    def pretty_label(n: str) -> str:
        d = parse_dump_date_token(n)
        return display_long(d) if d else n

    entry = {
        "runDate":      day,
        "apiVersion":   api,
        "title":        title,
        "oldDumpLabel": pretty_label(old_src.name),
        "newDumpLabel": pretty_label(new_src.name),
        "detailHref":   f"{day}/index.html",
        "compareHref":  f"{day}/codecomp.html"
    }
    existing.append(entry)
    seen = set(); merged = []
    for r in sorted(existing, key=lambda x: x["runDate"]):
        if r["detailHref"] in seen: continue
        seen.add(r["detailHref"]); merged.append(r)
    write_text(db, json.dumps(merged, ensure_ascii=False, indent=2))

    # Render master index
    mtpl = read_text(P["tpl"] / "index_template.html")
    if not mtpl:
        sys.exit(f"[ERROR] Missing template: {P['tpl'] / 'index_template.html'}")
    master_html = inject_master(mtpl, merged, "assets/cadence-logo.png", chips_html(req))
    write_text(P["work"] / "index.html", master_html)

    # Success email with links (requires public_base_url)
    base_url = cfg.get("links", "public_base_url", fallback="").rstrip("/")
    if base_url:
        master_url  = f"{base_url}/index.html"
        detail_url  = f"{base_url}/{day}/index.html"
        compare_url = f"{base_url}/{day}/codecomp.html"
        send_mail(cfg,
            f"[ProdvsProd] Report built {day}",
            f"Master Index: {master_url}\n"
            f"Detailed Page: {detail_url}\n"
            f"Diff Report:   {compare_url}\n"
        )

    # Auto-update lastdumpcomp.date to NEW dump
    write_text(P["last"], new_src.name + "\n")

    append_text(log, f"[{dt.datetime.now().isoformat(timespec='seconds')}] Run end\n")
    print(f"[DONE] {run}\n  Detailed: {run/'index.html'}\n  Compare:  {run/'codecomp.html'}\n  Master:   {P['work']/'index.html'}")

if __name__ == "__main__":
    main()
