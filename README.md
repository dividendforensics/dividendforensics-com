# Dividend Forensics Bureau

Publication site for the Dividend Forensics Bureau — independent structural
research on dividend durability across REITs, business development companies
and other income assets.

https://dividendforensics.com

## Structure

| Page | Purpose |
|---|---|
| `index.html` | Home |
| `learn.html` | Educational series index |
| `reit-*.html` | Individual Learn chapters |
| `research.html` | Published work, grouped by sector |
| `tools.html` | Free checklist and guides |
| `about.html` | Method, frameworks, scope |
| `legal.html` `privacy.html` `disclaimer.html` `Refund.html` | Policy pages |

Retired pages from the previous site forward to their nearest equivalent
with a canonical link and `noindex`. Their originals are kept in `_legacy/`.

Static HTML on GitHub Pages. `dfb.css` holds every shared style.

`articles.json` is the canonical source for the home and research listings. Run
`python build_site.py` after editing it; the GitHub Actions workflow performs the
same build on `main`. The older files under `data/` and `tools/` are retained for
reference but are not part of the active publishing path.
