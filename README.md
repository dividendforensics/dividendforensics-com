# Dividend Forensics Bureau

Independent, filing-anchored research on capital structure, debt, dilution,
financing, refinancing, credit and payout mechanics. Production site: https://dividendforensics.com

## The editorial edition

Warm paper, oxblood and serif-led typesetting for the publication; a separate
forest-ink Research Desk for professional inquiries. The visual evidence is
from the original reports, not generated artwork. A premium presentation does
not imply a paid subscription is available. Membership remains **not open**.

## Public copy state — 2026-09-24

DFB remains Dividend Forensics Bureau, with analysis by Jeong-Mo Goo. Public
positioning is method-led rather than limited to dividend-paying companies.
Existing REIT/BDC research, field guides and the published MAA/WPC working
paper are preserved; historical article findings are not rewritten for branding.
The three named income frameworks remain reference material on Methodology,
not the front-door description of the publication.

Membership is removed from shared navigation and launch-notice promotion.
`membership.html` remains a status-only URL: in preparation, not open for
enrollment or payment, no public price or launch date. Do not upload review-only
Weekly or MRP sample files, enable checkout, or publish internal pricing through
a copy change. The existing free Report No. 001 checkout is a separate, already
published MAA/WPC working paper; preserve its variant ID.

Active social destinations are Benzinga, Stocktwits, Muck Rack, X and Bluesky.
Substack is no longer promoted. The Research Desk form is preserved as an
inquiry route, not represented as a live paid custom-research or data product.


## Publishing one article

1. Verify the public article URL, byline and publication date. An internal
   contributor preview is not a published article.
2. Add a record near the top of the root `articles.json` array. Array order is
   editorial order. Use `status: "published"` only for a public article.
3. Run `python build_site.py` and the checks below, or commit the data and let
   `.github/workflows/main.yml` build, check and request a Pages deployment.

Required fields: `url`, `title`, `blurb`, `date`, `group`, `label`, `case_key`.
Optional: `case_slug`, `home` (boolean), `home_title`, `related_report`, `revision`,
`status` (`published`, `draft`, `internal_review`). Dates use `YYYY-MM-DD` or,
for historical records without a verified day, `YYYY-MM`.

An existing local `case-{case_slug}.html` is used when available. Otherwise the
reader goes directly to the public external article, with its destination
clearly labelled. The builder does not invent a case page or a public URL.
Drafts and internal-review items are never rendered. Duplicate URLs, invalid
slugs, impossible dates and contributor-preview URLs stop the build.

The site displays **the number of selected public research records**, not an
unaudited lifetime publication total. `published_count` is a retained legacy
running count and is not used in the public interface. Latest-publication dates
come from the most recent dated public record, not the current date or the
first row. No manual timestamp update is needed.

## Files that own the design

- `dfb.css`: design tokens, typography, accessible navigation, footer, common UI.
- `newsroom.css`: publication, archive, field guides, tools, case files, policies.
- `research-desk.css`: preserved desk components with the dark editorial theme.
- `site.js`: optional menu and archive search/filter enhancement; no tracking.
- `templates/header.html` and `templates/footer.html`: shared site chrome.
- `templates/home.html` and `templates/research.html`: home/archive body sources.
- `build_site.py`: validates records, renders the home/archive and shared chrome.
- `tools/redesign_site.py`: **one-time migration**, retained for provenance;
  it is not the publishing entry point and must not run in normal CI.
- `tools/render_social.py`: recreates the four typographic social-preview PNGs.

The builder owns `ARTICLES`, `SITE:HEADER`, and `SITE:FOOTER` marker regions.
Do not manually edit generated content inside them. Other HTML content stays
editable. Templates preserve the original report checkout ID. The Research
Desk keeps its existing FormSubmit endpoint and normal form POST; browser tests
validate fields without sending mail.

## Verification

```
python build_site.py
python build_site.py --check
python -m unittest discover -s tests -v
python tools/check_site.py
```

Browser checks additionally require `beautifulsoup4` and `playwright`:

```
python -m pip install beautifulsoup4 playwright
python -m playwright install chromium
python tools/browser_check.py --output /tmp/dfb-preview
```

The browser suite renders all 28 active pages at 320, 390, 768, 1024 and 1440px.
It checks horizontal overflow, images, archive search, sector filters, empty
states, mobile menu, Escape focus, form validity, no-JavaScript reading and a
nested missing URL. It never submits a form or follows external article links.
`--inline` is available in environments that prohibit localhost requests.

`.github/workflows/design-review.yml` runs this suite on design branches/PRs and
uploads screenshots. The main publishing workflow explicitly requests a Pages
build after any generated HTML commit: a bot commit alone does not trigger
branch-based Pages publishing.

## Preservation and recovery

The 2026-09-17 redesign started from commit
`8de223e70ee50a93a715e00ab3b7cd9d2e1ef2e7`.
Original report cover/reconciliation/ladder images, research text, legal notices,
CNAME, Google verification and retired redirects are preserved. Old root
`buildsite.yml` is archived as `_legacy/buildsite-before-editorial.yml`.
The older `data/` and legacy build scripts under `tools/` are **not active**.

Revert the single editorial-redesign release commit to restore the previous
site. Do not replace the report checkout variant or the custom domain when
reverting a visual change.
