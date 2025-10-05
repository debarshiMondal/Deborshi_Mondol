#!/usr/bin/env bash
set -euo pipefail

ENV="${1:-}"
if [[ -z "${ENV}" ]]; then
  echo "Usage: $0 <ENV>"
  exit 1
fi

# -------------------------------------------------------------------
# OUTPUT
# -------------------------------------------------------------------
OUT_DIR="/data/public/pmd_rule/${ENV}"
mkdir -p "${OUT_DIR}"
rm -f "${OUT_DIR}"/*

# -------------------------------------------------------------------
# INPUTS
#   Current PMD (new path you provided)
#   Original PMD (unchanged path; update here if yours changed too)
# -------------------------------------------------------------------
CURR_CLASSES="PMDReport/currentpmdoutput/changeSetDeploy/force-app/main/default/classes"
CURR_TRIGGERS="PMDReport/currentpmdoutput/changeSetDeploy/force-app/main/default/triggers"

ORG_CLASSES="PMDReport/orgpmdoutput/src/classes"
ORG_TRIGGERS="PMDReport/orgpmdoutput/src/triggers"

HTML_WORK="PMDReport/html"
mkdir -p "${HTML_WORK}"

# -------------------------------------------------------------------
# HIGHLIGHT PATTERN (same as your script)
# -------------------------------------------------------------------
PATTERN='ApexUnitTestShouldNotUseSeeAllDataTrue|UnusedLocalVariable|ClassNamingConventions|FieldDeclarationsShouldBeAtStart|FieldNamingConventions|FormalParameterNamingConventions|LocalVariableNamingConventions|MethodNamingConventions|PropertyNamingConventions|ExcessiveClassLength|ExcessiveParameterList|ApexDoc|ApexCSRF|AvoidDirectAccessTriggerMap|AvoidHardcodingId|AvoidNonExistentAnnotations|EmptyCatchBlock|EmptyIfStmt|EmptyStatementBlock|EmptyTryOrFinallyBlock|EmptyWhileStmt|InaccessibleAuraEnabledGetter|MethodWithSameNameAsEnclosingClass|OverrideBothEqualsAndHashcode|TestMethodsMustBeInTestClasses|AvoidDmlStatementsInLoops|AvoidSoqlInLoops|AvoidSoslInLoops|OperationWithLimitsInLoop|ApexBadCrypto|ApexDangerousMethods|ApexInsecureEndpoint|ApexOpenRedirect|ApexSharingViolations|ApexSOQLInjection|ApexSuggestUsingNamedCred'

# -------------------------------------------------------------------
# HELPERS
# -------------------------------------------------------------------
escape_html() {
  # Escapes &, <, > in a stream
  sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g'
}

make_table() {
  # make_table <infile> <outfile>
  local in="$1" out="$2"
  {
    echo '<table class="list"><tbody>'
    if [[ -f "$in" ]]; then
      awk -v pat="$PATTERN" '
        function esc(s){ gsub(/&/,"&amp;",s); gsub(/</,"&lt;",s); gsub(/>/,"&gt;",s); return s }
        {
          line=$0
          klass = ($0 ~ pat) ? " class=\"bad\"" : ""
          printf("<tr><td%s>%s</td></tr>\n", klass, esc(line))
        }
      ' "$in"
    else
      echo '<tr><td class="dim">[No file found]</td></tr>'
    fi
    echo '</tbody></table>'
  } > "$out"
}

build_page() {
  # build_page <TYPE:Class|Trigger> <display_name> <org_file> <curr_file> <html_out>
  local typ="$1" name="$2" orgf="$3" currf="$4" html="$5"

  local org_count="0" curr_count="0"
  [[ -f "$orgf" ]] && org_count="$(wc -l < "$orgf" | awk '{print $1}')"
  [[ -f "$currf" ]] && curr_count="$(wc -l < "$currf" | awk '{print $1}')"

  local org_tbl cur_tbl
  org_tbl="$(mktemp)"; cur_tbl="$(mktemp)"
  trap 'rm -f "$org_tbl" "$cur_tbl"' RETURN

  make_table "$orgf" "$org_tbl"
  make_table "$currf" "$cur_tbl"

  local now
  now="$(date '+%d %b %Y, %I:%M %p %Z')"

  # ---------- HTML ----------
  cat > "$html" <<EOF
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>${name} – Original vs Current PMD</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  :root{
    --bg:#0a0f1a; --ink:#e5e7eb; --dim:#a1a1aa; --line:#1f2937;
    --card:#0b1220; --card2:#0d1426; --accent:#ef4444; --ok:#22c55e;
  }
  *{box-sizing:border-box}
  html,body{margin:0;padding:0;background:var(--bg);color:var(--ink);
    font:14px/1.6 system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Cantarell,"Helvetica Neue",Arial,"Noto Sans",sans-serif}
  .wrap{max-width:1200px;margin:0 auto;padding:20px}
  header{border-bottom:1px solid var(--line);padding:18px 0 14px}
  .title{margin:0;font-weight:900;font-size:22px;letter-spacing:.2px}
  .subtitle{color:var(--dim);font-size:12px}
  .chip{
    display:inline-block;margin-left:8px;padding:2px 8px;border-radius:999px;
    border:1px solid #14532d;background:#0b2b1a;color:#86efac;font-size:12px;font-weight:700
  }
  .grid{display:grid;gap:16px;margin-top:18px;grid-template-columns:repeat(2,minmax(0,1fr))}
  @media (max-width:900px){.grid{grid-template-columns:1fr}}
  .card{border:1px solid var(--line);border-radius:14px;overflow:hidden;
        background:linear-gradient(180deg,var(--card),#091020);box-shadow:0 6px 24px rgba(0,0,0,.25)}
  .head{display:flex;justify-content:space-between;align-items:center;background:var(--card2);padding:12px 14px;border-bottom:1px solid var(--line)}
  .head h2{margin:0;font-size:16px}
  .stat{font-weight:800}
  .stat.ok{color:var(--ok)}
  .stat.bad{color:var(--accent)}
  .pad{padding:12px}
  .list{width:100%;border-collapse:collapse}
  .list td{padding:8px 10px;border-bottom:1px dashed #1b2437;vertical-align:top}
  .list tr:hover{background:rgba(239,68,68,.08)}
  .list td.dim{color:var(--dim)}
  .list td.bad{background:Tomato;color:#000;font-weight:700}
  footer{margin-top:22px;background:#000;color:#fff;padding:16px 20px;text-align:center;border-top:1px solid #111}
  .end{font-weight:800;letter-spacing:.3px}
</style>
</head>
<body>
  <div class="wrap">
    <header>
      <h1 class="title">${typ}: ${name}</h1>
      <div class="subtitle">Original vs Current PMD • Generated: ${now}</div>
    </header>

    <section class="grid">
      <div class="card">
        <div class="head">
          <h2>Original PMD Warnings</h2>
          <div class="stat ${org_count=="0" && echo ok || echo bad}">${org_count}</div>
        </div>
        <div class="pad">
EOF
  cat "$org_tbl" >> "$html"
  cat >> "$html" <<'EOF'
        </div>
      </div>

      <div class="card">
        <div class="head">
          <h2>Current PMD Warnings</h2>
          <!-- COUNT_PLACEHOLDER -->
        </div>
        <div class="pad">
EOF
  # Insert current count with class
  if [[ "$curr_count" == "0" ]]; then
    sed -i "s/<!-- COUNT_PLACEHOLDER -->/<div class=\"stat ok\">${curr_count}<\/div>/" "$html"
  else
    sed -i "s/<!-- COUNT_PLACEHOLDER -->/<div class=\"stat bad\">${curr_count}<\/div>/" "$html"
  fi

  cat "$cur_tbl" >> "$html"
  cat >> "$html" <<'EOF'
        </div>
      </div>
    </section>

    <footer><div class="end">End of the Report.</div></footer>
  </div>
</body>
</html>
EOF
}

# -------------------------------------------------------------------
# PROCESS: CLASSES
#   current:  .../classes/*.txt   (e.g., MyClass.cls_currpmd.txt)
#   original: PMDReport/orgpmdoutput/src/classes/MyClass.cls_orgpmd.txt
#   output :  PMDReport/html/MyClass.cls_orgpm.html
# -------------------------------------------------------------------
if [[ -d "$CURR_CLASSES" ]]; then
  while IFS= read -r -d '' currfile; do
    base="$(basename "$currfile")"                                      # MyClass.cls_currpmd.txt
    display="$(echo "$base" | sed 's/\.cls_currpmd\.txt$/.cls/')"       # MyClass.cls
    orgbase="$(echo "$base" | sed 's/currpmd/orgpmd/')"                 # MyClass.cls_orgpmd.txt
    orgfile="${ORG_CLASSES}/${orgbase}"

    htmlname="$(echo "$base" | sed 's/\.txt$/_orgpm.html/')"            # MyClass.cls_orgpm.html
    htmlout="${HTML_WORK}/${htmlname}"

    build_page "Class" "$display" "$orgfile" "$currfile" "$htmlout"
  done < <(find "$CURR_CLASSES" -type f -name '*.txt' -print0)
fi

# -------------------------------------------------------------------
# PROCESS: TRIGGERS
#   current:  .../triggers/*.txt   (e.g., MyTrig.trigger_currpmd.txt)
#   original: PMDReport/orgpmdoutput/src/triggers/MyTrig.trigger_orgpmd.txt
#   output :  PMDReport/html/MyTrig.trigger_orgpm.html
# -------------------------------------------------------------------
if [[ -d "$CURR_TRIGGERS" ]]; then
  while IFS= read -r -d '' currfile; do
    base="$(basename "$currfile")"                                             # MyTrig.trigger_currpmd.txt
    display="$(echo "$base" | sed 's/\.trigger_currpmd\.txt$/.trigger/')"      # MyTrig.trigger
    orgbase="$(echo "$base" | sed 's/currpmd/orgpmd/')"                        # MyTrig.trigger_orgpmd.txt
    orgfile="${ORG_TRIGGERS}/${orgbase}"

    htmlname="$(echo "$base" | sed 's/\.txt$/_orgpm.html/')"                   # MyTrig.trigger_orgpm.html
    htmlout="${HTML_WORK}/${htmlname}"

    build_page "Trigger" "$display" "$orgfile" "$currfile" "$htmlout"
  done < <(find "$CURR_TRIGGERS" -type f -name '*.txt' -print0)
fi

# -------------------------------------------------------------------
# COPY OUT
# -------------------------------------------------------------------
cp -f "${HTML_WORK}/"*"_orgpm.html" "${OUT_DIR}/" 2>/dev/null || true
echo "✔ Pages written to: ${OUT_DIR}"
