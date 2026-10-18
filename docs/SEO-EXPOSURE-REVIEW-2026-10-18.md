# SEO exposure review — 18 October 2026

## Evidence and scope
The supplied external report is an input, not proof of Google indexing or approval. This follow-up inspected local HTML and generators and current Google documentation. No Search Console, AdSense account, search-volume, backlink or mail-delivery evidence was available.

## Changes
- Added a 96px PNG and multi-resolution ICO using the existing D monogram, with stable icon links on active pages. The original SVG is retained. Google's current documented formats list raster formats and ICO; icon display is not guaranteed.
- Changed the shared masthead from “Analysis by Jeong-Mo Goo” to “About Jeong-Mo Goo.” The masthead is a biography link, not an assertion that every educational page is personally authored or reviewed. DFB Education remains the educational article attribution, matching its visible label and editorial policy.
- Connected the two existing personally attributed REIT articles to the existing about-page Person identifier. No qualifications, reviews or holdings were invented.
- Added WebPage metadata to four existing field guides, without inventing publication dates or personal authorship. Added practical reading links to the new comparison and worksheet; industrial and telecom pages explicitly retain their own cash-flow definitions.
- Kept AdSense ownership metadata and ads.txt intact. No advertising scripts, analytics, forms, scheduled collection or external messages were activated.

## Corrections to the submitted audit
- The current sitemap has 107 URLs, following three practical guides; 104 is the earlier release count.
- The six older guides had 2,232–4,299 main-content characters before these edits. The two older REIT articles already had Article metadata. Four field guides lacked JSON-LD, now supplemented with WebPage metadata.
- A 1,000-character or fixed word-count threshold is not a Google approval rule. Google explicitly says it has no preferred word count. Counts help identify candidates for editorial review; they cannot prove usefulness or approval.
- YMYL search-quality considerations and AdSense review are distinct. A disclaimer does not replace accurate sources, definitions, periods and calculations.
- REIT vs BDC, dividend dates, and the research worksheet were already implemented and deployed in PR #8. They are not new proposals awaiting implementation.

## Validation
- Python: 117 tests passed.
- Static checker: 119 active pages passed.
- SEO checker: 107 indexable pages / 107 sitemap URLs, zero errors, two existing advisory warnings.
- Build idempotence checked; favicon visually inspected at 96px.
- Main-text sample: 60 English learn-/reit-/field-guide pages, minimum 2,232 characters. This includes headings and links within main, excludes shared header/footer, and is not a quality score.
- This follow-up did not repeat the full mobile/desktop rendering suite or every calculator scenario. PR #8's earlier checks remain separate evidence.

## Remaining work
Search Console ownership, sitemap processing, exclusions and query impressions require account evidence. Do not describe sitemap inclusion as successful Google indexing. Verify actual issuer filings before publishing a real-company numerical walkthrough. Do not add unverified Substack ownership or assumed personal holdings. The proposed BDC rate experiment remains a future content/tool project, not a deployed feature.

## Official sources
- https://developers.google.com/search/docs/appearance/favicon-in-search
- https://developers.google.com/search/docs/fundamentals/creating-helpful-content
- https://developers.google.com/search/docs/appearance/ai-features

## Focused independent review request
Inspect the deployed PNG/ICO links, retained AdSense verification, biography masthead versus article authors, the two REIT Person links, and four field-guide WebPage records. Check that original publication dates remain unchanged and new links resolve. Report observed defects with URL, reproduction and evidence; distinguish source inspection from browser execution and account access. Do not treat text length, schema presence or these tests as approval/ranking guarantees.

Publication status: local validation complete; remote deployment verification is pending at the time of this record.
