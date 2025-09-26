#!/usr/bin/env bash
set -euo pipefail

# --------------------------------------------------------------------
# Original Combined PMD Report (HTML + CSV)
# - Input PMD lines:  PMDReport/orgpmdoutput/src/classes/*.txt
#                     PMDReport/orgpmdoutput/src/triggers/*.txt
# - Input detail HTML: PMDReport/htmlorg/*  (copied to output dir)
# - Output folder:     /data/public/PMDOUTPUT/$ENV
# - Output files:      index.html
#                      Original_Combined_PMD_Report.csv
# --------------------------------------------------------------------

ENV="${1:-}"
if [[ -z "${ENV}" ]]; then
  echo "Usage: $0 <ENV>"
  exit 1
fi

OUTPUT_DIR="/data/public/PMDOUTPUT/${ENV}"
INDEX_FILE="${OUTPUT_DIR}/index.html"
CSV_FILE="${OUTPUT_DIR}/Original_Combined_PMD_Report.csv"
DETAIL_SRC="PMDReport/htmlorg"
PMD_CLASSES_DIR="PMDReport/orgpmdoutput/src/classes"
PMD_TRIGGERS_DIR="PMDReport/orgpmdoutput/src/triggers"

mkdir -p "${OUTPUT_DIR}"

# Clean previous HTML/CSV in output (keep any other artifacts)
rm -f "${INDEX_FILE}" "${CSV_FILE}"
# Optional: clear previous copied HTML details (but keep the folder)
find "${OUTPUT_DIR}" -maxdepth 1 -type f -name "*.html" ! -name "index.html" -exec rm -f {} +

# Prepare temp row buffers
CLASSES_TMP="$(mktemp)"
TRIGGERS_TMP="$(mktemp)"
trap 'rm -f "${CLASSES_TMP}" "${TRIGGERS_TMP}"' EXIT

# CSV header
printf 'Type,Name,PMD_Issues,Link\n' > "${CSV_FILE}"

# Dedup guards
declare -A seen_classes
declare -A seen_triggers

# Helper: safe CSV cell
csv_cell() {
  # Escape double quotes by doubling them, then wrap in quotes
  local s="${1//\"/\"\"}"
  printf '"%s"' "$s"
}

# ---------- Collect class rows ----------
shopt -s nullglob
if [[ -d "${PMD_CLASSES_DIR}" ]]; then
  for fpath in "${PMD_CLASSES_DIR}"/*.txt; do
    fname="$(basename "$fpath")"

    # Expect pattern: <Name>.cls_orgpmd.txt  -> display: <Name>.cls
    display="${fname%.cls_orgpmd.txt}.cls"
    # Fallback if pattern different: just remove trailing _orgpmd.txt
    if [[ "${display}" == "${fname}" ]]; then
      display="${fname%_orgpmd.txt}"
    fi

    # De-dup by display name
    if [[ -n "${display}" && -n "${seen_classes[$display]:-}" ]]; then
      continue
    fi
    seen_classes["$display"]=1

    # Count PMD issues by line count (keep consistent with existing logic)
    # shellcheck disable=SC2002
    count="$(wc -l < "$fpath" | awk '{print $1}')"

    # Derive detail HTML name. Common patterns:
    #   <Name>.cls.html  (typical)
    #   Fallback: strip any spaces
    html_name="${display}.html"
    link="${html_name}"

    # Append HTML row
    printf '<tr><td class="name"><a href="%s">%s</a></td><td class="num">%s</td></tr>\n' \
      "$link" "$display" "$count" >> "${CLASSES_TMP}"

    # Append CSV row
    {
      csv_cell "Class"; printf ','
      csv_cell "${display}"; printf ','
      csv_cell "${count}"; printf ','
      csv_cell "${link}"; printf '\n'
    } >> "${CSV_FILE}"
  done
fi

# ---------- Collect trigger rows ----------
if [[ -d "${PMD_TRIGGERS_DIR}" ]]; then
  for fpath in "${PMD_TRIGGERS_DIR}"/*.txt; do
    fname="$(basename "$fpath")"

    # Expect pattern: <Name>.trigger_orgpmd.txt -> display: <Name>.trigger
    display="${fname%.trigger_orgpmd.txt}.trigger"
    if [[ "${display}" == "${fname}" ]]; then
      display="${fname%_orgpmd.txt}"
    fi

    # De-dup by display name
    if [[ -n "${display}" && -n "${seen_triggers[$display]:-}" ]]; then
      continue
    fi
    seen_triggers["$display"]=1

    count="$(wc -l < "$fpath" | awk '{print $1}')"
    html_name="${display}.html"
    link="${html_name}"

    printf '<tr><td class="name"><a href="%s">%s</a></td><td class="num">%s</td></tr>\n' \
      "$link" "$display" "$count" >> "${TRIGGERS_TMP}"

    {
      csv_cell "Trigger"; printf ','
      csv_cell "${display}"; printf ','
      csv_cell "${count}"; printf ','
      csv_cell "${link}"; printf '\n'
    } >> "${CSV_FILE}"
  done
fi
shopt -u nullglob

# ---------- Copy detail HTML pages to output (if any) ----------
if [[ -d "${DETAIL_SRC}" ]]; then
  # Copy only *.html, keep existing if none new
  find "${DETAIL_SRC}" -maxdepth 1 -type f -name "*.html" -exec cp -f {} "${OUTPUT_DIR}/" \;
fi

# ---------- Totals ----------
classes_total="$(wc -l < "${CLASSES_TMP}" | awk '{print $1}')"
triggers_total="$(wc -l < "${TRIGGERS_TMP}" | awk '{print $1}')"
now="$(date '+%d %b %Y, %I:%M %p %Z')"

# ---------- Write HTML ----------
cat > "${INDEX_FILE}" <<EOF
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Original Combined PMD Report</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  :root {
    --bg: #0f172a;
    --card: #0b1220;
    --ink: #e5e7eb;
    --ink-dim: #a1a1aa;
    --accent: #4f46e5;
    --accent-2: #06b6d4;
    --line: #1f2937;
    --good: #22c55e;
  }
  html, body {
    margin:0; padding:0; background:#0a0f1a; color:var(--ink); font: 14px/1.6 system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, "Helvetica Neue", Arial, "Noto Sans", sans-serif;
  }
  .wrap { max-width: 1100px; margin: 0 auto; padding: 24px; }
  header {
    border-bottom: 1px solid var(--line);
    padding: 28px 0 18px;
  }
  .title {
    font-size: 28px; font-weight: 800; letter-spacing: 0.2px;
    background: linear-gradient(90deg, #fff, #c7d2fe, #99f6e4);
    -webkit-background-clip: text; background-clip: text; color: transparent;
    margin: 0 0 6px 0;
  }
  .meta { color: var(--ink-dim); font-size: 12px; }
  .toolbar {
    margin-top: 18px; display: flex; gap: 12px; flex-wrap: wrap;
  }
  .btn {
    display:inline-block; padding: 10px 16px; border-radius: 999px;
    background: linear-gradient(180deg, #8b5cf6, #4f46e5 60%, #0ea5e9);
    color: #fff; text-decoration: none; font-weight: 700; letter-spacing: .2px;
    box-shadow: 0 10px 18px rgba(79,70,229,.35), inset 0 1px 0 rgba(255,255,255,.35);
    transition: transform .12s ease, box-shadow .12s ease, filter .12s ease;
    border: 0;
  }
  .btn:hover { transform: translateY(-1px); filter: brightness(1.05); }
  .grid {
    margin-top: 24px; display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 18px;
  }
  @media (max-width: 900px){ .grid { grid-template-columns: 1fr; } }
  .card {
    background: linear-gradient(180deg, #0b1220, #091020);
    border: 1px solid var(--line); border-radius: 16px; overflow: hidden;
    box-shadow: 0 6px 24px rgba(0,0,0,.25);
  }
  .card h2 {
    font-size: 16px; margin: 0; padding: 14px 16px;
    border-bottom: 1px solid var(--line); background: #0d1426;
  }
  .pill {
    display:inline-block; margin-left:8px; padding: 2px 8px; font-size: 12px; border-radius: 999px;
    background: #0b2b1a; color: #86efac; border: 1px solid #14532d;
  }
  table {
    width: 100%; border-collapse: collapse;
  }
  thead th {
    text-align: left; font-weight: 700; color:#cbd5e1;
    font-size: 12px; letter-spacing: .3px; text-transform: uppercase;
    padding: 10px 12px; background: #0e1529; border-bottom: 1px solid var(--line);
  }
  tbody td {
    padding: 10px 12px; border-bottom: 1px dashed #1b2437;
    vertical-align: middle;
  }
  tbody tr:hover { background: rgba(79,70,229,.08); }
  td.name a {
    color:#e5e7eb; text-decoration:none; font-weight:600;
  }
  td.name a:hover { text-decoration: underline; }
  td.num { text-align: right; font-variant-numeric: tabular-nums; }
  footer {
    margin-top: 28px; background: #000; color:#fff; padding: 18px 24px; text-align: center;
    border-top: 1px solid #111;
  }
  .end { opacity:.9; font-weight:700; letter-spacing: .3px; }
</style>
</head>
<body>
  <div class="wrap">
    <header>
      <div class="title">Original Combined PMD Report</div>
      <div class="meta">Environment: <strong>${ENV}</strong> &nbsp;•&nbsp; Generated: ${now}</div>
      <div class="toolbar">
        <a class="btn" href="Original_Combined_PMD_Report.csv" download>Download as CSV</a>
      </div>
    </header>

    <section class="grid">
      <div class="card">
        <h2>Classes <span class="pill">${classes_total}</span></h2>
        <table>
          <thead><tr><th>Name</th><th style="text-align:right">PMD Issues</th></tr></thead>
          <tbody>
$(cat "${CLASSES_TMP}")
          </tbody>
        </table>
      </div>

      <div class="card">
        <h2>Triggers <span class="pill">${triggers_total}</span></h2>
        <table>
          <thead><tr><th>Name</th><th style="text-align:right">PMD Issues</th></tr></thead>
          <tbody>
$(cat "${TRIGGERS_TMP}")
          </tbody>
        </table>
      </div>
    </section>

    <footer>
      <div class="end">End of the Report.</div>
    </footer>
  </div>
</body>
</html>
EOF

echo "✔ Wrote: ${INDEX_FILE}"
echo "✔ Wrote: ${CSV_FILE}"
echo "✔ Copied detail HTML to: ${OUTPUT_DIR}"
