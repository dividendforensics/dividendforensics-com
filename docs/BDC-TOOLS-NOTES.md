# BDC worksheets — implementation and review record

Date: 2026-10-18. This is a development record, not an external professional certification or a statement that the pages have been deployed. The parent release task controls integration and deployment.

## Implemented scope

`bdc_tools.py` exports `TOOLS` and `outputs(root)`. The five static pages are:

1. `/calculator-bdc-nii-pik.html` — NII, PIK and common-distribution worksheet.
2. `/calculator-bdc-pik-ratios.html` — PIK/TII versus PIK/NII.
3. `/calculator-bdc-non-accrual.html` — separate non-accrual cost and fair-value denominators.
4. `/calculator-bdc-nav-discount.html` — user-entered common-share price/NAV premium or discount.
5. `/calculator-bdc-leverage.html` — gross and optional cash-adjusted debt/common-equity; no statutory asset-coverage verdict.

Each page contains original explanations, a synthetic worked example, formulas, filing input locations, interpretation, limitations, FAQs, primary-source links, named author and actual publication date. All substantive explanations are static HTML. No actual company result is preloaded or asserted to have been independently verified. Browser inputs are labeled synthetic until edited, then user scenario. No account, ad script, live quote, SEC browser request, network transmission of inputs or persistent input storage is added.

The script `/bdc-calculators.js` follows the pinned `/vendor/decimal.js/decimal.js` dependency. Root integration must retain the final `bureau.css` injection used by `build_site.planned_outputs`; this provides responsive select/textarea sizing as well as the navy/ivory/brass design.

## Arithmetic and data safeguards

- Decimal.js clone: 40 significant digits, half-up rounding. Values stay decimal strings; display is rounded to four decimal places only. Tiny nonzero values use scientific notation.
- Empty, not found, not disclosed, not applicable and explicit zero remain distinct in input records. An unavailable supplement prevents total distributions and total coverage, while valid regular coverage remains available.
- NII = −10 with regular distributions = 100 retains −0.1000× signed coverage. PIK/NII is not interpreted for nonpositive NII. A zero divisor displays an explicit zero-denominator reason; missing inputs display a missing-input reason.
- Same validator handles `manual` and `extracted` pure-function records. Input overrides inconsistent with common currency, scale, amount/per-share unit, period, date, reported/adjusted basis, common scope or declared/paid basis are rejected.
- The public UI supports total amounts for four tools and directly entered per-share currency units only for price/NAV. There is no weighted-average/current-share conversion, quarter/YTD conversion, FX conversion or implicit annualization.
- Per-input notes retain source URL, accession and document locator. Output audit includes formula version `bdc-1.0.0`, formula, input IDs, raw strings, dates, units, availability, origin and source fields; absent reviewer/retrieval metadata stays null.
- Common-context selectors are reader assertions. A calculator cannot discover that a pasted number actually came from another period without its metadata. This limitation is explicit in the pages.
- All PIK sensitivity columns are simple hypothetical deductions, not cash earnings, cash flow, cash available for distribution or a loss forecast. No safety score, grade, buy/sell recommendation or legal compliance conclusion exists.
- Invalid decimal syntax (commas, exponent notation, NaN/Infinity, excessive length) is rejected. Negative NII/NAV/common equity remains allowed where meaningful; ordinary PIK income and distributions cannot be negative. PIK reversals require a separately reconciled analysis rather than a silently reclassified entry.
- Editing clears stale results and requests recalculation. Reset restores the synthetic example; clearing amounts keeps them missing rather than inserting zeros.

## ZIP acceptance fixture

Synthetic USD million for a common quarter: NII 120, included PIK 18, TII 180, regular 100, supplemental 10, special 5. Total distributions = 115. Regular coverage = 1.2000×; total coverage = 1.0435×; PIK/TII = 10.0000%; PIK/NII = 15.0000%.

| Simple PIK deduction | Income | Regular coverage | Total coverage |
|---|---:|---:|---:|
| 0% | 120 | 1.2000× | 1.0435× |
| 25% | 115.5 | 1.1550× | 1.0043× |
| 50% | 111 | 1.1100× | 0.9652× |
| 100% | 102 | 1.0200× | 0.8870× |

## Actual verification

Windows PowerShell, installed Node.js, Python 3.13, Playwright and installed Google Chrome.

| Command / check | Actual result |
|---|---|
| `node --test tests/bdc-calculators.test.cjs` | PASS, 21 tests. Fixture, all sensitivities, missing/zero/negative values, invalid input, metadata mismatch, dates, decimal precision, other four worksheets and audit data. |
| `python -m unittest discover -s tests -p test_bdc_tools.py -v` | PASS, 3 tests. Five substantive static pages, unique H1/canonicals/IDs, explicit input labels, local links, dependency order and static safeguards. |
| Isolated local HTTP server with final `build_site.planned_outputs` and Chrome | PASS, five tools × 360/768/1440 widths = 15 renders; no page overflow or JavaScript exceptions; invalid input → correction/reset works on each tool. Missing supplemental, signed negative NII, availability selector and clear/reset checked in actual UI. No SEC browser request observed. |
| Desktop/mobile screenshot inspection | Generated and visually inspected `.qa/bdc-desktop.png` and `.qa/bdc-mobile.png`; final shared CSS used. An initial harness omitted `bureau.css` and showed overflow; corrected the harness to final build outputs and reran successfully. |
| Print-event and stale-result follow-up | PASS in a minimal network-free Chrome document using the actual vendor and BDC scripts: `beforeprint` opens all six input source disclosures plus the output audit; `afterprint` restores their closed state; editing clears the previous result. A separate broader HTTP follow-up stalled under shared browser load and was stopped, so it is not counted as an additional pass. |

Browser checks used a temporary server serving generated HTML without overwriting shared build outputs. Tests did not call real SEC endpoints repeatedly. They did not submit external forms, send email or activate a scheduler. Source definitions were researched separately through official Investor.gov/SEC material.

## Limits / not run

- No verified real-issuer worksheet is claimed. Public examples are synthetic. A future company snapshot requires sourced figures, matching dates/definitions and an actual review record.
- No human screen-reader audit, physical-phone test, actual printer test or claim of WCAG certification.
- The source-and-audit disclosure is interactive on screen. `beforeprint` expands input source notes and output audit records, then `afterprint` restores their state; period/unit/formula/limitations also remain in visible output and static text. Physical print layout still needs a human check.
- No CSV import/export, automatic issuer dataset extraction or live-price feed is added to these five worksheets. The separate filing pipeline is outside this module.
- Full-site regression, AdSense account submission and public deployment are parent-task responsibilities; these local results do not establish them.

## Primary sources consulted

- [Investor.gov: Publicly Traded Business Development Companies — Investor Bulletin](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins/publicly-traded-business-development-companies-bdcs-investor-bulletin): BDC structure, expenses, distributions and market-price/NAV relationship.
- [SEC issuer filing: PIK income and non-accrual accounting policy](https://www.sec.gov/Archives/edgar/data/1859919/000185991925000013/bdc-20241231.htm): an issuer-specific policy example, not a universal definition or source of this tool's synthetic amounts.
- [SEC EDGAR search](https://www.sec.gov/edgar/search/): readers must obtain the current original filing and reconcile the specific definition before entering company data.

## Independent review prompt

Review the five pages listed above and `bdc_tools.py`, `bdc-calculators.js`, and their tests. Distinguish actual code/UI observations from developer claims and checks you did not run. Independently recompute the ZIP fixture and all four sensitivity columns. Test missing supplemental, missing PIK, missing TII, zero distributions, negative NII, mixed period/currency/scale/basis records and invalid decimal input. Check non-accrual population consistency, the price/NAV sign, and whether debt/equity is ever mistaken for statutory asset coverage. Inspect 360px layout, keyboard behavior, stale-result clearing, source records and a printed worksheet. Report severity, exact file/page, reproducible input, expected versus actual behavior and a minimal fix. Do not infer AdSense approval or human financial verification from a passing test suite.
