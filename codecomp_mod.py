from pathlib import Path
from collections import Counter
import shutil

def beautify_codecomp_html(codecomp_path: Path,
                           out_copy_at_run_root: Path,
                           old_label: str,   # previous dump (LHS)
                           new_label: str,   # latest dump (RHS)
                           new_counts: Counter,        # per-metadata "New" counts
                           modified_counts: Counter):  # per-metadata "Modified" counts
    """
    Replace the raw Beyond Compare HTML with a minimal, beautiful summary page:
      - Header: title, LHS/RHS dump names, logo, and back button.
      - One table: [Metadata Type | File Changes (Total) | New | Modified]
        * Metadata Type rendered as a blue, clickable-looking pill button with hover uplift.
      - Footer only.

    Writes back to `codecomp_path` and also copies to `out_copy_at_run_root` if provided.
    """
    # Union of all metadata types present in either counter
    metas = sorted(set(new_counts.keys()) | set(modified_counts.keys()), key=lambda s: s.lower())

    def row(meta: str) -> str:
        new_n = int(new_counts.get(meta, 0))
        mod_n = int(modified_counts.get(meta, 0))
        tot_n = new_n + mod_n
        return (
            f"<tr>"
            f'  <td><button class="meta-btn" type="button" aria-label="Open {meta}">{meta}</button></td>'
            f'  <td><span class="num black">{tot_n}</span></td>'
            f'  <td><span class="num green">{new_n}</span></td>'
            f'  <td><span class="num orange">{mod_n}</span></td>'
            f"</tr>"
        )

    rows_html = (
        "\n".join(row(m) for m in metas)
        if metas else '<tr><td colspan="4" class="empty">No differences detected.</td></tr>'
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Code Comparison Report — {old_label} vs {new_label}</title>
<style>
  :root{{
    --blue:#1d4ed8; --blue-deep:#1e40af;
    --green:#16a34a;
    --orange:#d97706;
    --gray:#6b7280; --ink:#0b0f19; --line:#e6e9ef; --bg:#f8fafc; --white:#fff;
    --radius:16px; --shadow:0 8px 24px rgba(0,0,0,.08),0 2px 6px rgba(0,0,0,.06);
  }}
  *,*::before,*::after{{box-sizing:border-box}}
  body{{margin:0;background:var(--bg);color:var(--ink);font:14px/1.5 system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Cantarell,Noto Sans,sans-serif}}

  /* Header */
  header{{background:linear-gradient(135deg,#0b0f19 0%,var(--blue-deep) 100%);color:#fff}}
  .h-inner{{max-width:1100px;margin:0 auto;padding:14px 18px;display:flex;align-items:center;justify-content:space-between;gap:12px}}
  .h-title{{display:flex;flex-direction:column;gap:6px}}
  .h-title h1{{margin:0;font-size:clamp(18px,2.2vw,24px);font-weight:900;letter-spacing:.2px}}
  .badges{{display:flex;gap:8px;flex-wrap:wrap}}
  .badge{{background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.28);color:#fff;padding:4px 10px;border-radius:999px;font-size:12px}}
  .brand{{display:flex;align-items:center;gap:8px}}
  .brand img{{height:32px;display:block;filter:drop-shadow(0 2px 2px rgba(0,0,0,.35))}}
  .back{{display:inline-flex;align-items:center;gap:6px;font-weight:700;font-size:12px;
         background:rgba(255,255,255,.10);border:1px solid rgba(255,255,255,.35);
         border-radius:999px;padding:4px 8px;color:#fff;text-decoration:none}}
  .back:hover{{background:rgba(255,255,255,.18)}}

  main{{max-width:1100px;margin:18px auto;padding:0 18px}}

  /* Single card */
  .card{{background:#fff;border:1px solid var(--line);border-radius:var(--radius);box-shadow:var(--shadow);padding:18px}}

  /* The one table */
  table.summary{{width:100%;border-collapse:separate;border-spacing:0 10px}}
  table.summary th, table.summary td{{text-align:left;padding:10px 12px}}
  table.summary thead th{{font-size:12px;color:#111;letter-spacing:.3px;border-bottom:1px solid var(--line)}}
  table.summary tbody tr{{background:#fff;border:1px solid var(--line)}}
  table.summary tbody td{{border-top:1px solid var(--line);border-bottom:1px solid var(--line)}}
  table.summary tbody tr td:first-child{{border-left:1px solid var(--line);border-top-left-radius:12px;border-bottom-left-radius:12px}}
  table.summary tbody tr td:last-child{{border-right:1px solid var(--line);border-top-right-radius:12px;border-bottom-right-radius:12px}}

  /* Clickable feel for metadata type */
  .meta-btn{{
    background:var(--blue); color:#fff; border:none; border-radius:999px;
    padding:8px 12px; font-weight:800; cursor:pointer; box-shadow:0 2px 6px rgba(0,0,0,.12);
    transition:transform .15s ease, box-shadow .15s ease, filter .15s ease;
  }}
  .meta-btn:hover{{ transform:translateY(-1px); box-shadow:0 6px 14px rgba(0,0,0,.18); filter:brightness(1.05); }}
  .meta-btn:active{{ transform:translateY(0); box-shadow:0 3px 8px rgba(0,0,0,.14); }}

  /* Colored numbers */
  .num{{display:inline-block;min-width:30px;text-align:center;font-weight:900}}
  .num.black{{color:#111}}
  .num.green{{color:var(--green)}}
  .num.orange{{color:var(--orange)}}
  .empty{{text-align:center;color:var(--gray)}}

  footer{{background:#0b0f19;color:#fff;text-align:center;font-size:12px;padding:6px 10px;margin-top:24px}}
</style>
</head>
<body>
<header>
  <div class="h-inner">
    <div class="h-title">
      <h1>Code Comparison Report</h1>
      <div class="badges">
        <span class="badge">LHS (Previous): <strong>{old_label}</strong></span>
        <span class="badge">RHS (Latest): <strong>{new_label}</strong></span>
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

    # Write page and copy alias if requested
    codecomp_path.parent.mkdir(parents=True, exist_ok=True)
    codecomp_path.write_text(html, encoding="utf-8")
    if out_copy_at_run_root:
        out_copy_at_run_root.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(codecomp_path, out_copy_at_run_root)
