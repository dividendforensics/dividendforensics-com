# Filing-lab source and production record — 2026-10-18

Scope: two fixed historical FY2024 educational exercises and one index. These are not current issuer assessments, dividend forecasts, ratings, recommendations or an AdSense approval claim. The source ledger is `content/filing-labs.json`; rendering and decimal calculations are in `filing_labs.py`.

## Production and verification

The exercises were researched, drafted and implemented with automated assistant assistance as part of the user's requested parallel work. The delegated agent compared primary-source table inputs, and the parent independently checked the principal source rows. No human professional review, investment credential, personal holding, first-hand investment experience or issuer endorsement is asserted. This internal production record is distinct from the public educational material.

Primary disclosures were browsed on October 18, 2026. Realty Income's SEC-hosted release and 10-K were readable directly. The large Ares Capital original 10-K initially failed through the browsing tool; the parent fetched the original SEC document to the ignored `.qa/arcc-2024-source.html`, and this agent independently parsed that complete document to confirm the PIK rows, distributions, NII, Core EPS context and fee policy. Search excerpts were not the final numerical verification for those rows. No copied filing or large source snapshot is added to this module's tracked deliverables.

## Source inventory

| Source | Document date | Accession | Locations used |
| --- | --- | --- | --- |
| [Realty Income FY2024 earnings release, Exhibit 99.1](https://www.sec.gov/Archives/edgar/data/726728/000072672825000049/o-991q42024.htm) | 2025-02-24 | 0000726728-25-000049 | p.2 dividends; p.8 annual per-share figures; p.9 FFO/Normalized FFO; p.10 AFFO; Glossary |
| [Realty Income FY2024 Form 10-K](https://www.sec.gov/Archives/edgar/data/726728/000072672825000055/o-20241231.htm) | 2025-02-25 | 0000726728-25-000055 | Item 7 AFFO table; Note 17A p.81, monthly distributions and January 2025 payable amount; Note 4B, investments in existing properties |
| [Ares Capital FY2024 earnings release, Exhibit 99.1](https://www.sec.gov/Archives/edgar/data/1287750/000128775025000004/arccq4-2024exhibit991.htm) | 2025-02-05 | 0001287750-25-000004 | p.1 operating results and basic-share convention; p.8 income/expenses; p.9 Schedule 1 Core EPS |
| [Ares Capital FY2024 Form 10-K](https://www.sec.gov/Archives/edgar/data/1287750/000128775025000007/arcc-20241231.htm) | 2025-02-05 | 0001287750-25-000007 | p.F-6 operations and PIK categories; p.F-144 equity; p.F-145 cash flows and supplemental declared distributions; Income Based Fee policy and risk discussion p.44 |
| [Ares Capital FY2024 Form 10-K/A](https://www.sec.gov/Archives/edgar/data/1287750/000128775025000012/arcc-20241231.htm) | 2025-03-24 | 0001287750-25-000012 | Explanatory Note and signatures |

The ARCC amendment adds separate IHAM statements and makes exhibit/certification changes. Its explanatory note states the original 10-K is otherwise unchanged. March 20 is a share-count snapshot appearing on the cover, not the amendment signature date. The ledger uses March 24.

## Date and unit contract

All analytical flows use January 1–December 31, 2024. The year-end annualized Realty Income dividend and monthly amount payable are explicitly marked as point-in-time rates with `periodStart: null`.

Every fact uses a decimal **string**, a source URL, a source identifier, a table/row locator, a basis, currency/scale, period end, provenance and check date. JSON numbers/floats, missing source metadata, mismatched period ends and mismatched source publication dates are rejected.

- `asOf` means the measurement date or reporting-period end. It does **not** mean the information was publicly available on that date. The schema documents this meaning.
- `availableFrom` is the publication date of the cited document. The public source list displays these 2025 dates, and public prose distinguishes publication from measurement.
- `checkedOn` is October 18, 2026, the check date for this historical exercise.
- The BDC calculator handoff uses analysis as-of **2026-10-18**, not the historical report end, because that calculator asks for an analysis date.
- REIT reconciliation amounts are USD thousands; diluted weighted-average shares are thousands of shares. Per-share amounts are USD per share. The separate property-spending context uses the issuer's rounded USD millions.
- BDC aggregate inputs are USD millions. NII/Core EPS inputs use the issuer's **basic** per-share convention. No aggregate amount is manufactured from per-share data and a share count.

## Independent reconstruction — Realty Income

FFO 3,467,659 + normalization 96,292 = Normalized FFO 3,563,951 (USD thousands). The complete signed adjustments after Normalized FFO are:

`+5,116 +32,741 +15,361 +13,935 +106,801 -8,558 -402 -171,887 +55,870 +3,552 -2,078 +7,035 = +57,486`

Common AFFO is therefore 3,621,437. Adding 6,599 attributable to dilutive noncontrolling interests yields diluted AFFO 3,628,036; dividing by 865,842 thousand diluted weighted-average shares yields approximately 4.1901825, displayed by the issuer as 4.19.

The annual cash dividend is **3.1255** per share from the detailed table and 10-K monthly schedule. The release narrative rounds this to 3.126; the lab preserves the more precise detailed input.

- Per-share paid-dividend payout: `3.1255 / 4.19 * 100 = 74.5943%`.
- Per-share coverage: `4.19 / 3.1255 = 1.3406x`.
- Aggregate common paid-dividend payout: `2,691,719 / 3,621,437 * 100 = 74.3274%`.
- Common AFFO less aggregate paid distributions: `929,718` USD thousand, explicitly described as an arithmetic excess, not cash on hand.
- Year-end annualized rate: `0.2640 * 12 = 3.168`; dividing that rate by annual AFFO produces `75.6086%`, a different temporal comparison. The 0.2640 amount was payable at December 31, 2024 and paid in January 2025.

The page explains both the attribution adjustment in diluted AFFO and the different share/time populations behind aggregate payment totals and weighted-average diluted earnings. It does not force aggregate and per-share ratios to agree.

The narrow recurring-capex adjustment is distinguished from the 10-K's separate disclosure of 122.9 million capitalized on existing properties, including 113.9 million classified as non-recurring improvements. No alternative maintenance-capex estimate is invented. Costs already deducted in AFFO must not be deducted a second time.

## Independent reconstruction — Ares Capital

Full-year investment income: `2,162 + 172 + 594 + 62 = 2,990` USD million. Expenses: `715 + 374 + 364 + 18 + 12 + 31 = 1,514`. After tax 73, reported NII is `1,403`.

The 10-K reports aggregate common dividends declared and payable of **1,219** million (equity statement and cash-flow supplemental information). Cash dividends paid are **1,139** million in financing cash flows. These are not silently substituted for one another. The stockholders' equity statement also shows 80 million of shares issued under the dividend-reinvestment plan; the lab does not build a generalized reconciliation of settlement timing from this identity.

- Aggregate reported NII coverage: `1,403 / 1,219 = 1.1509x`.
- Separately reported basic per-share NII coverage: `2.25 / 1.92 = 1.1719x`.
- Issuer Core EPS bridge: `2.44 - 0.19 + 0.03 + 0.05 = 2.33`.
- Core EPS coverage: `2.33 / 1.92 = 1.2135x`; labeled non-GAAP and not substituted for reported NII.

Five source PIK rows on p.F-6 were independently confirmed:

| Income category | Non-controlled/non-affiliate | Non-controlled affiliate | Controlled affiliate | Computed total |
| --- | ---: | ---: | ---: | ---: |
| PIK interest | 174 | 14 | 18 | 206 |
| PIK dividends | 253 | No separately labeled PIK-dividend row used | 4 | 257 |

Total recognized PIK is **463**, not the interest-only subtotal 206. This is a gross income component. `463 / 2,990 = 15.4849%` of total investment income; `463 / 1,403 = 33.0007%` when scaled against reported NII after expenses/tax. The latter is not described as a fraction of net cash earnings or a proof of ultimate noncollection.

Sensitivity holds expenses, incentive fees, tax, collections and all other items unchanged:

| Fraction of PIK removed | Constructed income, USD million | Declared-distribution coverage |
| --- | ---: | ---: |
| 0% | 1,403.00 | 1.1509x |
| 25% | 1,287.25 | 1.0560x |
| 50% | 1,171.50 | 0.9610x |
| 100% | 940.00 | 0.7711x |

The 100% row is neither a default/loss forecast nor cash earnings. The fee policy and risk discussion establish why accrued but uncollected income and incentive fees require separate investigation. The lab does not assume a fee refund, model hurdles/catch-up provisions, or infer liquidity from a coverage crossing.

## Validation and limits

`python -m unittest discover -s tests -p test_filing_labs.py -v` passed **10 tests** on October 18, 2026. Tests independently reconstruct the main equations with `fractions.Fraction`, compare them with Decimal results, enforce source dates and dimensions, reject altered signs/scales/invalid denominators, and inspect all generated pages and internal links. The renderer uses 40 significant-digit Decimal arithmetic and half-up display rounding; source rounding still limits economic precision.

`outputs(root)` produced three complete HTML strings through the existing education shell without writing generated pages. `cards(root, sector=None)` supports both sectors or a REIT/BDC filter. Parent integration, full-site tests, browser layout inspection and any deployment are separate tasks. This module adds no forms, trackers, live data API, account flow or calculator JavaScript.

Future annual cases should receive new dated inputs and a new exercise, or an explicitly recorded revision after checking every formula and answer. Do not silently label these FY2024 examples as current. Unit tests verify recorded arithmetic and metadata, not the truth of underlying issuer estimates, completeness of future disclosures, or future distributions.
