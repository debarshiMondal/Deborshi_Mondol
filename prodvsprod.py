#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
prodvsprod.py

Generates a dated run folder under /data/public/ProdvsProdComp/YYYY-MM-DD/
containing:
  - copied Previous and Latest dump folders
  - CSVs (full/new/removed) — full CSV named: ProdDumpComparison_List_{EXECDATE}(Execution Date).csv
  - run.log
  - detailed report page (index.html) linking to:
        - Previous/Latest dump folders
        - CSV Report Link (SharePoint, if configured) or local CSV
        - Diff Only Code Comparison Report (./codecomp.html)
        - Run Log

Also updates:
  - /data/public/ProdvsProdComp/reports.json (append this run)
  - /data/public/ProdvsProdComp/index.html (master index) using templates/index_template.html

Key behaviors:
  - Reads PREVIOUS dump name from lastdumpcomp.date (exits + email if empty/missing)
  - Uses latest folder in dumps_root as LATEST
  - Validates top-level folder set parity; validates configured required metadata presence
  - Optionally runs external compare shell (codecompare.posix2.sh) with folder NAMES (not full paths)
  - Titles formatted as: "Production Dump Comparison: {Long Old Date} vs. {Long New Date}"
  - Master index card title uses the same string; sub-pills show humanized dates
  - One absolute logo path for both pages via [ui] logo_abs

Config (setup.conf) — important keys:
[paths]
dumps_root        = /backup/PROD_DUMP
work_root         = /data/public/ProdvsProdComp
compare_script_dir= /softwere/codedev/misc_script/SFDC/BCompareScript
lastdump_file     = /path/to/lastdumpcomp.date
templates_dir     = /path/to/templates
assets_dir        = /path/to/assets           ; (not required by this script, kept for compatibility)

[ui]
logo_abs = /ProdvsProdComp/assets/cadence-logo.png
api_version_fallback = 62.0

[compare]
run_external_compare = true

[metadata]
current_sfdc_metadata_list_used_in_cadence = classes, objects, triggers, pages

[links]
# If set, Detailed page "CSV Report Link" opens SharePoint URL.
# Use {EXEC_DATE} placeholder (e.g., 8Sept2025). Parentheses are part of the filename.
csv_full_sharepoint_pattern = https://cadence-my.sharepoint.com/:x:/r/personal/somraj_global_cadence_com/Documents/Config%20Dev%20Ops/WeeklyMasterUpdate/ProdDumpComparison_List_{EXEC_DATE}(Execution Date).csv

[mail]
method = mutt                  ; mutt | smtp | sendmail
to = you@example.com, team@example.com

[smtp]
host = smtp.example.com
port = 587
user =
password =
from =
starttls = true

[advanced]
# Optional backdate override for importing legacy runs (YYYY-MM-DD). If blank, uses today.
run_date_override =
"""

import os, re, csv, sys, json, shutil, hashlib, subprocess, datetime as dt
from collections import Counter
from configparser import ConfigParser
from pathlib import Path
from email.mime.text import MIMEText
import smtplib

# ---------- basic FS helpers ----------
def load_conf(p: Path)->ConfigParser:
    if not p.exists():
        sys.exit(f"[ERROR] Missing config: {p}")
    c=ConfigParser()
    c.read(p)
    return c

def read_text(p:Path)->str:
    return p.read_text(encoding="utf-8") if p.exists() else ""

def write_text(p:Path,s:str):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(s,encoding="utf-8")

def append_text(p:Path,s:str):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("a",encoding="utf-8") as f:
        f.write(s)

def copy_tree(src:Path,dst:Path):
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src,dst)

def sha256(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for ch in iter(lambda:f.read(1024*1024), b""):
            h.update(ch)
    return h.hexdigest()

def find_latest_dump(root:Path)->Path:
    c=[p for p in root.iterdir() if p.is_dir()]
    if not c:
        sys.exit(f"[ERROR] No dumps under {root}")
    c.sort(key=lambda p:p.stat().st_mtime, reverse=True)
    return c[0]

def top_level_dirs(p:Path)->set:
    return {x.name for x in p.iterdir() if x.is_dir()}

def walk_files(base:Path):
    for r,_,fs in os.walk(base):
        for f in fs:
            full=Path(r)/f
            yield full.relative_to(base), full

# ---------- dates & labels ----------
DATE_TOKEN_RE = re.compile(r'(\d{1,2})(?:st|nd|rd|th)?([A-Za-z]+)(\d{4})')

MONTH_MAP = {
    "jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,"jul":7,"aug":8,
    "sep":9,"sept":9,"oct":10,"nov":11,"dec":12
}
MONTH_ABBR_FOR_EXEC = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",7:"Jul",8:"Aug",9:"Sept",10:"Oct",11:"Nov",12:"Dec"}
MONTH_LONG = {1:"January",2:"February",3:"March",4:"April",5:"May",6:"June",7:"July",8:"August",9:"September",10:"October",11:"November",12:"December"}

def ordinal(n:int)->str:
    return f"{n}{'th' if 11<=n%100<=13 else {1:'st',2:'nd',3:'rd'}.get(n%10,'th')}"

def parse_dump_date_token(name: str):
    """
    Extract tokens like '4thSept2025', '10thAug2025', '4thSep2025' from dump folder names.
    Returns datetime.date or None.
    """
    m = DATE_TOKEN_RE.search(name)
    if not m:
        return None
    day = int(m.group(1))
    mon_token = m.group(2).lower()
    year = int(m.group(3))
    # normalize to a known key — 'sep' and 'sept' both → 9
    key = "sept" if mon_token.startswith("sep") else mon_token[:3]
    month = MONTH_MAP.get(key)
    if not month:
        return None
    try:
        return dt.date(year, month, day)
    except ValueError:
        return None

def display_long(d:dt.date)->str:
    return f"{ordinal(d.day)} {MONTH_LONG[d.month]} {d.year}"

def exec_date_token(d:dt.date)->str:
    """e.g., 8Sept2025 for SharePoint filename token"""
    return f"{d.day}{MONTH_ABBR_FOR_EXEC[d.month]}{d.year}"

# ---------- email ----------
def send_mail(cfg:ConfigParser, subj:str, body:str):
    method=cfg.get("mail","method",fallback="mutt").strip().lower()
    rcpts=[x.strip() for x in cfg.get("mail","to",fallback="").split(",") if x.strip()]
    if not rcpts:
        return
    try:
        if method=="mutt":
            subprocess.run(["mutt","-s",subj,*rcpts],input=body.encode(),check=False)
        elif method=="sendmail":
            msg=f"Subject: {subj}\nTo: {', '.join(rcpts)}\n\n{body}"
            subprocess.run(["/usr/sbin/sendmail","-t","-oi"],input=msg.encode(),check=False)
        else:
            host=cfg.get("smtp","host"); port=cfg.getint("smtp","port",fallback=587)
            user=cfg.get("smtp","user",fallback=""); pwd=cfg.get("smtp","password",fallback="")
            sender=cfg.get("smtp","from",fallback=user or "noreply@example.com")
            use_tls=cfg.getboolean("smtp","starttls",fallback=True)
            msg=MIMEText(body,"plain","utf-8"); msg["Subject"]=subj; msg["From"]=sender; msg["To"]=", ".join(rcpts)
            with smtplib.SMTP(host,port,timeout=45) as s:
                s.ehlo()
                if use_tls: s.starttls(); s.ehlo()
                if user: s.login(user,pwd)
                s.sendmail(sender,rcpts,msg.as_string())
    except Exception as e:
        print(f"[WARN] mail failed: {e}", file=sys.stderr)

# ---------- HTML helpers ----------
def counts_to_html(counter:Counter)->str:
    if not counter:
        return '<div class="note">N/A</div>'
    items=[f'<li><span class="t">{t}</span><span class="c">{n}</span></li>'
           for t,n in sorted(counter.items(), key=lambda kv:(-kv[1],kv[0].lower()))]
    return '<ul class="typecounts">'+"".join(items)+'</ul>'

def chips_html(items)->str:
    return ('<div class="chips">'+"".join(f'<span class="chip meta">{x}</span>' for x in items)+'</div>') if items \
           else '<div class="note">No metadata configured.</div>'

def render_detail_html(tpl:str, **kw)->str:
    out=tpl
    for k,v in kw.items():
        out=out.replace("{{"+k+"}}", str(v))
    return out

def render_master_html_js(tpl:str, reports:list, logo_abs:str, meta_html:str)->str:
    js=json.dumps(reports,ensure_ascii=False).replace("</script>","<\\/script>")
    return tpl.replace("{{REPORT_CARDS_JSON}}",js)\
              .replace("{{CADENCE_LOGO}}",logo_abs)\
              .replace("{{METADATA_SIDEBAR_HTML}}",meta_html)
              
def beautify_codecomp_report(run_dir: Path,
                             prev_name: str,
                             latest_name: str,
                             cnt_new: Counter,
                             cnt_chg: Counter,
                             logo_href: str):
    """
    Wraps the raw Beyond Compare HTML in a branded, navigable page:
      - Renames codecomp.html -> codecomp.raw.html (if exists)
      - Creates a new codecomp.html with header, footer, badges, buttons, and a summary table
      - Embeds raw report via <iframe>
    """
    orig = run_dir / "codecomp.html"
    if not orig.exists():
        return  # nothing to do (e.g., run_external_compare = false)
    raw = run_dir / "codecomp.raw.html"
    try:
        if raw.exists():
            raw.unlink()
        orig.rename(raw)
    except Exception:
        # If we cannot rename, leave the original in place and just wrap via iframe src="codecomp.html"
        raw = orig

    # Build per-metadata counts
    all_types = sorted(set(cnt_new.keys()) | set(cnt_chg.keys()), key=str.lower)
    rows = []
    buttons = []
    for t in all_types:
        n = int(cnt_new.get(t, 0))
        m = int(cnt_chg.get(t, 0))
        tot = n + m
        # Button (blue, white text) shows metadata + total
        buttons.append(
            f'<a class="mtype-btn" href="#summary-table" title="{t} — {tot} changes">'
            f'{t}<span class="cc">{tot}</span></a>'
        )
        # Table row
        rows.append(
            f'<tr>'
            f'<td class="t">{t}</td>'
            f'<td class="tot">{tot}</td>'
            f'<td class="new">{n}</td>'
            f'<td class="mod">{m}</td>'
            f'</tr>'
        )

    # Which side is which — we ran the shell with "-o old -o new"
    left_label = prev_name
    right_label = latest_name

    # If we failed to rename, i.e., raw == orig, keep iframe src to "codecomp.html"
    iframe_src = "codecomp.raw.html" if raw.name != "codecomp.html" else "codecomp.html"

    html = f"""<!DOCTYPE html>
        <html lang="en">
        <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Diff Only Code Comparison Report</title>
        <style>
          :root {{
            --blue:#1d4ed8; --blue-deep:#1e40af; --ink:#0b0f19; --bg:#f8fafc; --line:#e6e9ef; --white:#fff;
            --green:#15803d; --orange:#b45309; --muted:#6b7280;
            --shadow:0 8px 24px rgba(0,0,0,.08),0 2px 6px rgba(0,0,0,.06);
            --radius:14px;
          }}
          *,*::before,*::after{{box-sizing:border-box}}
          html,body{{height:100%}}
          body{{
            margin:0;background:var(--bg);color:var(--ink);
            font:14px/1.5 system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Cantarell,Noto Sans,sans-serif;
            display:flex;flex-direction:column;min-height:100vh;
          }}

          /* Header */
          header{{background:linear-gradient(135deg,#0b0f19 0%,var(--blue-deep) 100%);color:#fff;box-shadow:var(--shadow)}}
          .h-inner{{max-width:1100px;margin:0 auto;padding:14px 18px;display:flex;align-items:center;justify-content:space-between;gap:12px}}
          .h-title{{display:flex;flex-direction:column;gap:6px}}
          .h-title h1{{margin:0;font-size:clamp(18px,2.2vw,24px);font-weight:900;letter-spacing:.2px}}
          .badges{{display:flex;gap:8px;flex-wrap:wrap}}
          .badge{{background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.28);color:#fff;padding:4px 10px;border-radius:999px;font-size:12px}}
          .brand{{display:flex;align-items:center;gap:8px}}
          .brand img{{height:32px;display:block;filter:drop-shadow(0 2px 2px rgba(0,0,0,.35))}}
          .back{{display:inline-flex;align-items:center;gap:6px;font-weight:700;font-size:12px;background:rgba(255,255,255,.10);border:1px solid rgba(255,255,255,.35);border-radius:999px;padding:4px 8px;color:#fff;text-decoration:none}}
          .back:hover{{background:rgba(255,255,255,.18);text-decoration:none}}

          main{{max-width:1100px;margin:18px auto;padding:0 18px;flex:1 0 auto}}

          /* Buttons row */
          .btnrow{{display:flex;flex-wrap:wrap;gap:10px;margin:14px 0}}
          .mtype-btn{{
            display:inline-flex;align-items:center;gap:8px;
            background:linear-gradient(180deg,#1d4ed8,#1e40af); color:#fff;
            border:1px solid rgba(255,255,255,.2);
            border-radius:999px; padding:8px 12px; font-weight:800; text-decoration:none;
            box-shadow:0 4px 12px rgba(29,78,216,.28);
          }}
          .mtype-btn:hover{{filter:brightness(1.06)}}
          .mtype-btn .cc{{background:rgba(255,255,255,.15);border:1px solid rgba(255,255,255,.35);border-radius:999px;padding:2px 8px;font-size:12px}}

          /* Summary table card */
          .card{{background:#fff;border:1px solid var(--line);border-radius:var(--radius);box-shadow:var(--shadow);padding:16px;margin-top:10px}}
          table{{width:100%;border-collapse:collapse;font-size:14px}}
          thead th{{text-align:left;border-bottom:1px solid var(--line);padding:10px 8px;background:#f9fbff;color:#0f172a}}
          tbody td{{border-bottom:1px dashed var(--line);padding:8px}}
          td.t{{font-weight:800;color:#0f172a}}
          td.tot{{color:#111;font-weight:900}}
          td.new{{color:var(--green);font-weight:900}}
          td.mod{{color:var(--orange);font-weight:900}}
          .note{{color:var(--muted);font-size:13px;margin:10px 0}}

          /* Embed original diff */
          .iframe-wrap{{margin:16px 0 0;border:1px solid var(--line);border-radius:12px;overflow:hidden;box-shadow:var(--shadow)}}
          .iframe-wrap iframe{{width:100%;height:70vh;border:0;background:#fff}}

          footer{{background:#0b0f19;color:#fff;text-align:center;font-size:12px;padding:6px 10px;margin-top:24px}}
        </style>
        </head>
        <body>
        <header>
          <div class="h-inner">
            <div class="h-title">
              <h1>Diff Only Code Comparison Report</h1>
              <div class="badges">
                <span class="badge">Left: <strong>{left_label}</strong></span>
                <span class="badge">Right: <strong>{right_label}</strong></span>
              </div>
            </div>
            <div class="brand">
              <img src="{logo_href}" alt="Cadence logo" />
              <a class="back" href="./index.html">← Back</a>
            </div>
          </div>
        </header>

        <main>
          <div class="note">Below buttons summarise metadata with changes (New + Modified). Click to jump to the summary table.</div>
          <div class="btnrow">
            {''.join(buttons) if buttons else '<span class="note">No differences detected.</span>'}
          </div>

          <div id="summary-table" class="card">
            <table>
              <thead>
                <tr>
                  <th style="width:40%">Metadata Type</th>
                  <th style="width:20%">File Changes (Total)</th>
                  <th style="width:20%">New</th>
                  <th style="width:20%">Modified</th>
                </tr>
              </thead>
              <tbody>
                {''.join(rows) if rows else '<tr><td colspan="4" class="note">No differences to summarise.</td></tr>'}
              </tbody>
            </table>
          </div>

          <div class="iframe-wrap">
            <iframe src="{iframe_src}" title="Code comparison raw report"></iframe>
          </div>
        </main>

        <footer>This is the end of report.</footer>
        </body>
        </html>
        """
    write_text(run_dir / "codecomp.html", html)

              

# ---------- main ----------
def main():
    root=Path(__file__).resolve().parent
    cfg=load_conf(root/"setup.conf")

    P={
        "dumps": Path(cfg.get("paths","dumps_root",fallback="/backup/PROD_DUMP")),
        "work":  Path(cfg.get("paths","work_root", fallback="/data/public/ProdvsProdComp")),
        "script":Path(cfg.get("paths","compare_script_dir",fallback="/softwere/codedev/misc_script/SFDC/BCompareScript")),
        "last":  Path(cfg.get("paths","lastdump_file", fallback=str(root/"lastdumpcomp.date"))),
        "tpl":   Path(cfg.get("paths","templates_dir",  fallback=str(root/"templates"))),
    }

    # One absolute logo path for both pages
    logo_abs = cfg.get("ui","logo_abs",fallback="/ProdvsProdComp/assets/cadence-logo.png")
    api_fallback = cfg.get("ui","api_version_fallback",fallback="62.0")

    # Required metadata (top-level folders expected in both dumps)
    req_raw=cfg.get("metadata","current_sfdc_metadata_list_used_in_cadence",fallback="")
    req=[x.strip() for x in req_raw.split(",") if x.strip()]

    # Read previous dump name
    old_name=read_text(P["last"]).strip()
    if not old_name:
        send_mail(cfg,"[ProdvsProd] lastdumpcomp.date is empty",f"Populate {P['last']} with the PREVIOUS dump folder name.")
        sys.exit(1)
    old_src=P["dumps"]/old_name
    if not old_src.exists():
        send_mail(cfg,"[ProdvsProd] previous dump missing",f"Not found: {old_src}")
        sys.exit(1)

    new_src=find_latest_dump(P["dumps"])

    # Extract API version (from latest dump folder name), fallback if not present
    m=re.search(r"prod_([0-9.]+)_", new_src.name)
    api=m.group(1) if m else api_fallback

    # Build master/detailed title: "Production Dump Comparison: 10th August 2025 vs. 4th September 2025"
    d_old = parse_dump_date_token(old_src.name)
    d_new = parse_dump_date_token(new_src.name)
    if d_old and d_new:
        title = f"Production Dump Comparison: {display_long(d_old)} vs. {display_long(d_new)}"
    else:
        # fallback: just use tokens after prod_API_
        def fallback_label(n:str)->str:
            return n.replace(f"prod_{api}_","")
        title = f"Production Dump Comparison: {fallback_label(old_src.name)} vs. {fallback_label(new_src.name)}"

    # Determine run date (today or override)
    override = cfg.get("advanced","run_date_override",fallback="").strip()
    if override:
        try:
            run_date = dt.date.fromisoformat(override)
        except Exception:
            run_date = dt.date.today()
    else:
        run_date = dt.date.today()

    day = run_date.isoformat()
    run = P["work"]/day
    run.mkdir(parents=True, exist_ok=True)

    log = run/"run.log"
    write_text(log, f"[{dt.datetime.now().isoformat(timespec='seconds')}] Run start\nOld: {old_src}\nNew: {new_src}\n\n")

    # Copy dumps into run folder (keep ORIGINAL NAMES)
    prev_dir=run/old_src.name
    latest_dir=run/new_src.name
    copy_tree(old_src,prev_dir);   append_text(log,f"Copied -> {prev_dir}\n")
    copy_tree(new_src,latest_dir); append_text(log,f"Copied -> {latest_dir}\n")

    # Parity check: top-level folder names match (and count)
    tl_prev=top_level_dirs(prev_dir)
    tl_new =top_level_dirs(latest_dir)
    if tl_prev != tl_new:
        msg=(f"Top-level folder mismatch.\nPrev: {sorted(tl_prev)}\nLatest: {sorted(tl_new)}\nRun: {run}")
        append_text(log,"[ERROR] "+msg+"\n")
        send_mail(cfg,"[ProdvsProd] Folder name mismatch",msg)
        sys.exit(2)

    # Required metadata present?
    if req:
        miss_prev=[m for m in req if m not in tl_prev]
        miss_new =[m for m in req if m not in tl_new]
        if miss_prev or miss_new:
            msg=(f"Required metadata missing.\nRequired: {req}\nMissing in PREVIOUS ({old_src.name}): {miss_prev}\nMissing in LATEST ({new_src.name}): {miss_new}\nRun: {run}")
            append_text(log,"[ERROR] "+msg+"\n")
            send_mail(cfg,"[ProdvsProd] Required metadata missing in dumps",msg)
            sys.exit(3)

    # component.list for external compare
    comp_list = "\n".join(sorted(tl_prev))+"\n"
    write_text(P["script"]/ "component.list", comp_list)

    # Optionally run external compare (from run folder; pass folder names only)
    if cfg.getboolean("compare","run_external_compare",fallback=True):
        sh=P["script"]/ "codecompare.posix2.sh"
        if sh.exists():
            cmd=["bash",str(sh),"-d","-m","oo","-o",old_src.name,"-o",new_src.name]
            append_text(log,f"RUN: {' '.join(cmd)} (cwd={run})\n")
            subprocess.run(cmd,cwd=str(run),check=False)
        else:
            append_text(log,f"[WARN] Missing compare script: {sh}\n")

    # Compute diff lists
    prev={rel:f for rel,f in walk_files(prev_dir)}
    latest={rel:f for rel,f in walk_files(latest_dir)}

    new_files=[r for r in latest if r not in prev]
    changed=[]
    for r in sorted(set(prev)&set(latest)):
        a,b=prev[r], latest[r]
        if a.stat().st_size==b.stat().st_size and sha256(a)==sha256(b):
            continue
        changed.append(r)
    removed=[r for r in prev if r not in latest]

    # Folder-wise counts (top-level dir names)
    def top_folder(rel:Path)->str:
        return rel.parts[0] if rel.parts else "(root)"
    cnt_new=Counter(top_folder(r) for r in new_files)
    cnt_chg=Counter(top_folder(r) for r in changed)
    cnt_rm =Counter(top_folder(r) for r in removed)

    # CSV naming + SharePoint link substitution
    exec_token = exec_date_token(run_date)  # e.g., 8Sept2025
    full_csv_name = f"ProdDumpComparison_List_{exec_token}(Execution Date).csv"
    csv_full = run/full_csv_name
    csv_new  = run/"new_files_only.csv"
    csv_rm   = run/"removed_files_only.csv"

    cols=["File List","File Type","Dev Team Comment","PS team Comment","Ticket Number","Ticket Resolution Date","Area (Module)","Details of Change Made"]
    with csv_full.open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f); w.writerow(cols)
        for r in sorted(new_files):
            w.writerow([str(r),"New File","","","","","",""])
        for r in sorted(changed):
            w.writerow([str(r),"Content Mismatch","","","","","",""])

    with csv_new.open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f); w.writerow(["File List"])
        for r in sorted(new_files): w.writerow([str(r)])

    with csv_rm.open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f); w.writerow(["File List"])
        for r in sorted(removed): w.writerow([str(r)])

    append_text(log,f"CSV written: {csv_full.name}, {csv_new.name}, {csv_rm.name}\n")

    # Build “CSV Report Link” (SharePoint or local)
    sp_pattern = cfg.get("links","csv_full_sharepoint_pattern",fallback="").strip()
    if sp_pattern:
        csv_full_href  = sp_pattern.replace("{EXEC_DATE}", exec_token)
        csv_full_label = "CSV Report Link"
    else:
        csv_full_href  = f"./{full_csv_name}"
        csv_full_label = "Download CSV"

    # Detailed page
    dtpl = read_text(P["tpl"]/ "detail_template.html")
    if not dtpl:
        sys.exit(f"[ERROR] Missing template: {P['tpl']/ 'detail_template.html'}")

    # Labels shown in the summary table (we keep raw directory names for links)
    old_label = old_src.name
    new_label = new_src.name

    det = render_detail_html(
        dtpl,
        PAGE_TITLE=title, TITLE_HEADING=title,
        API_VERSION=api, REPORT_DATE=run_date.isoformat(),
        PREVIOUS_LABEL=old_label, LATEST_LABEL=new_label,
        PREVIOUS_LINK=f"./{old_src.name}/", LATEST_LINK=f"./{new_src.name}/",
        KPI_NEW=len(new_files), KPI_CHANGED=len(changed), KPI_REMOVED=len(removed),
        CSV_FULL=csv_full_href, CSV_FULL_LABEL=csv_full_label,
        CSV_NEW="./new_files_only.csv", CSV_REMOVED="./removed_files_only.csv",
        DIFF_HTML_LINK="./codecomp.html",
        TYPE_COUNTS_NEW=counts_to_html(cnt_new),
        TYPE_COUNTS_CHANGED=counts_to_html(cnt_chg),
        TYPE_COUNTS_REMOVED=counts_to_html(cnt_rm),
        RUN_LOG_LINK="./run.log",
        LOGO_HREF=logo_abs
    )
    write_text(run/"index.html", det)

    # Append to reports.json (master data)
    db = P["work"]/ "reports.json"
    try:
        existing = json.loads(read_text(db)) if db.exists() else []
    except Exception:
        existing = []

    def pretty_label(n:str)->str:
        d=parse_dump_date_token(n)
        return display_long(d) if d else n

    entry = {
        "runDate": day,
        "apiVersion": api,
        "title": title,
        "oldDumpLabel": pretty_label(old_src.name),
        "newDumpLabel": pretty_label(new_src.name),
        "detailHref": f"{day}/index.html",
        "compareHref": f"{day}/codecomp.html"
    }
    existing.append(entry)

    # De-dup by detailHref and keep chronological
    seen=set(); merged=[]
    for r in sorted(existing, key=lambda x:x["runDate"]):
        if r["detailHref"] in seen: continue
        seen.add(r["detailHref"])
        merged.append(r)

    write_text(db, json.dumps(merged, ensure_ascii=False, indent=2))

    # Rebuild master index
    mtpl = read_text(P["tpl"]/ "index_template.html")
    if not mtpl:
        sys.exit(f"[ERROR] Missing template: {P['tpl']/ 'index_template.html'}")
    index = render_master_html_js(mtpl, merged, logo_abs, chips_html(req))
    write_text(P["work"]/ "index.html", index)

    append_text(log, f"[{dt.datetime.now().isoformat(timespec='seconds')}] Run end\n")

    print(f"[DONE] {run}\n"
          f"  Detailed: {run/'index.html'}\n"
          f"  Compare:  {run/'codecomp.html'} (place if importing legacy)\n"
          f"  Master:   {P['work']/ 'index.html'}")

    # Beautify the Beyond Compare output page (if present)
    try:
        beautify_codecomp_report(run, old_src.name, new_src.name, cnt_new, cnt_chg, logo_abs)
    except Exception as e:
    append_text(log, f"[WARN] beautify_codecomp_report failed: {e}\n")



if __name__=="__main__":
    main()
