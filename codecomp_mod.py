from pathlib import Path
from collections import Counter
import shutil, re, html

def beautify_codecomp_html(codecomp_path: Path,
                           out_copy_at_run_root: Path,
                           old_label: str,               # LHS (Previous) folder name, e.g. "prod_62.0_10thAug2025_04:26:34"
                           new_label: str,               # RHS (Latest)   folder name, e.g. "prod_62.0_4thSept2025_04:26:34"
                           new_counts: Counter,          # per-top-level dir "New" counts, keys like "classes", "objects", etc.
                           modified_counts: Counter,     # per-top-level dir "Modified" counts
                           prev_human: str = None,       # e.g. "10th Aug 2025" (optional; auto-derives from old_label if None)
                           latest_human: str = None):    # e.g. "4th Sept 2025" (optional; auto-derives from new_label if None)
    """
    Build a minimal Diff-Only page WITHOUT reading raw HTML:
      - Header: "Code Comparison Report - Diff Only", badges:
          LHS (Previous): <prev_human>  vs  RHS (Latest): <latest_human>, logo + Back
      - One table: [Metadata Type | File Changes (Total) | New | Modified]
        * Each Metadata Type links to its deterministic path:
            If codecomp.html is inside .../_vs_/codecomp/ → "./<meta>/<meta>.html"
            Else (run root alias)                          → "<OLD>_vs_<NEW>/codecomp/<meta>/<meta>.html"
      - Footer stuck to end of page.

    No dependency on Beyond Compare's original HTML.
    """

    # Decide base href depending on where this pretty file lives
    if codecomp_path.parent.name == "codecomp":
        href_base = "."  # link like ./classes/classes.html
    else:
        href_base = f"{old_label}_vs_{new_label}/codecomp"

    # Normalize counts: keys are top-level folder names (e.g., "classes", "objects")
    n_l = {str(k).strip(): int(v) for k, v in (new_counts or {}).items()}
    m_l = {str(k).strip(): int(v) for k, v in (modified_counts or {}).items()}
    # Union of keys; keep natural order by name
    metas = sorted(set(n_l.keys()) | set(m_l.keys()), key=lambda s: s.lower())

    # Friendly date derivation if not provided
    def _human_from_name(name: str) -> str:
        # expect token like 10thAug2025 / 4thSept2025
        m = re.search(r'(\d{1,2})(?:st|nd|rd|th)?([A-Za-z]+)(\d{4})', name)
        if not m: return name
        day = int(m.group(1))
        mon = m.group(2).lower()
        year= int(m.group(3))
        mm = {"jan":"Jan","feb":"Feb","mar":"Mar","apr":"Apr","may":"May","jun":"Jun",
              "jul":"Jul","aug":"Aug","sep":"Sept","sept":"Sept","oct":"Oct","nov":"Nov","dec":"Dec"}
        mon_h = None
        for key in ("sept","sep","jan","feb","mar","apr","may","jun","jul","aug","oct","nov","dec"):
            if mon.startswith(key):
                mon_h = "Sept" if key in ("sep","sept") else mm[key]; break
        if not mon_h: return name
        suf = "th" if 11 <= day % 100 <= 13 else {1:"st",2:"nd",3:"rd"}.get(day % 10,"th")
        return f"{day}{suf} {mon_h} {year}"

    lhs_badge = prev_human or _human_from_name(old_label)
    rhs_badge = latest_human or _human_from_name(new_label)

    # Build table rows with deterministic links
    def row(meta: str) -> str:
        meta_dir = meta  # top-level folder name is the subdir
        # Compose deterministic href
        href = f"{href_base}/{meta_dir}/{meta_dir}.html"
        new_n = n_l.get(meta, 0)
        mod_n = m_l.get(meta, 0)
        tot_n = new_n + mod_n
        label = html.escape(meta)  # show directory name as-is
        return (
            f"<tr>"
            f'  <td><a class="meta-btn" href="{href}" target="_blank" rel="noopener">{label}</a></td>'
            f'  <td><span class="num black">{tot_n}</span></td>'
            f'  <td><span class="num green">{new_n}</span></td>'
            f'  <td><span class="num orange">{mod_n}</span></td>'
            f"</tr>"
        )

    rows_html = (
        "\n".join(row(m) for m in metas)
        if metas else '<tr><td colspan="4" class="empty">No differences detected.</td></tr>'
    )

    # Page HTML (header -> single table -> sticky footer)
    html_doc = f"""<!DOCTYPE html>
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
  table.summary tbody tr td:first-child{{border-left:1px solid var(--line); border-top-left-radiu
