# Operating-company source audit — October 18, 2026

Scope: one fixed historical Apple FY2024 filing lab. This is a financial-statement reading exercise, not a current issuer assessment, forecast, rating, recommendation or claim about an advertising program. The generator returns one page from `operating_filing_lab.outputs(root)`; it makes no network requests. `workbench_example(root)` provides the same verified inputs to the separately generated cash-flow workbench.

## Evidence and production record

The delegated assistant independently opened and read the full [SEC-hosted original Apple FY2024 Form 10-K](https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/aapl-20240928.htm), particularly pages 32–33, Note 1 page 34, Note 4 page 37 and Note 10 page 44. The original was accessible through the web tool on October 18, 2026. Search snippets and the earnings release helped locate the filing but were not the final numerical verification. The [SEC filing-details page](https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/0000320193-24-000123-index.html) confirms filing date November 1, 2024 and period of report September 28, 2024, accession 0000320193-24-000123.

The ledger contains **36 numeric source facts**, **one underlying 10-K**, and **two primary-source URLs** including the filing-details page. Two URLs do not mean two independent financial reports. No copied full filing is added to tracked deliverables. No human professional review, issuer endorsement, holding or first-hand investment experience is claimed.

## Measurement and availability

- Flow period: October 1, 2023–September 28, 2024, the issuer's 52-week FY2024. This is not calendar 2024.
- Beginning cash and shares: point-in-time September 30, 2023, with null `periodStart`.
- Ending cash, shares and the restricted-cash observation: point-in-time September 28, 2024.
- `asOf`: measurement date; for a flow, the period end.
- `availableFrom`: November 1, 2024, the cited filing's publication date. This does not assert that no earlier disclosure reported the same number. Apple released preliminary annual results on October 31; this exercise uses the filed 10-K.
- `checkedOn`: October 18, 2026. Rechecking the old filing does not update the historical inputs to 2026 financial results.
- Cash amounts use USD millions. Note 10 shares use thousands of shares. The restricted-cash note uses issuer-rounded USD billions, and declared dividend per share/RSU uses USD per share or RSU.

Each fact preserves its numeric value as a decimal string, a unit, currency where appropriate, reporting period, basis, source URL/ID, locator and provenance. The loader rejects numerical JSON floats, missing locators, mismatched units or dates, and inconsistent cash/share reconciliations. Source parentheses remain negative; the reported term-debt-issuance dash is explicitly encoded as zero.

## Independent arithmetic

All cash amounts below are USD millions.

| Calculation | Exact reconstruction |
| --- | --- |
| Reconciliation adjustments before changes in operating balances | 11,445 + 11,688 − 2,266 = 20,867 |
| Changes in operating assets and liabilities | −3,788 − 1,356 − 1,046 − 11,731 + 6,020 + 15,552 = 3,651 |
| Operating cash flow | 93,736 + 20,867 + 3,651 = 118,254 |
| Lab-defined FCF | 118,254 − 9,447 = 108,807 |
| Cash capital returns | 15,234 + 94,949 = 110,183 |
| FCF less cash dividends and repurchases | 108,807 − 110,183 = −1,376 |
| Net investing | −48,656 + 51,211 + 11,135 − 9,447 − 1,308 = 2,935 |
| Net financing | −5,441 − 15,234 − 94,949 + 0 − 9,958 + 3,960 − 361 = −121,983 |
| Cash change | 118,254 + 2,935 − 121,983 = −794 |
| Ending cash including restricted amounts | 30,737 − 794 = 29,943 |
| Residual-to-cash-change check | −1,376 + (2,935 + 9,447) + (−121,983 + 15,234 + 94,949) = −794 |

The share reconciliation is independently 15,550,061 − 499,372 + 66,097 = 15,116,786 **thousand shares**. Net decline is 433,275 thousand, which differs from gross repurchased shares. Repurchase dollars do not establish share-count reduction or repurchase value creation.

Cash dividends/equivalents of 15,234 differ from declared dividends/equivalents of 15,218 by 16. Cash repurchases of 94,949 differ from the shareholders' equity reduction of 95,846 by 897. The lab identifies the differing measurement bases; it does not invent a complete timing/tax reconciliation for these differences. The declared annual 0.98 per share or RSU is not multiplied by ending shares to manufacture aggregate cash payments.

## Interpretation and handoff constraints

The lab's FCF means operating cash flow less cash PP&E purchases. It is a stated non-GAAP analytical definition, not a separately reported GAAP subtotal or a claim that all residual cash can be distributed. It does not separate maintenance from growth capex. Investment-security flows, other investment, debt movements and equity-award settlement taxes are preserved in the full cash bridge. The $2.6 billion restricted-cash note is included as rounded context, not used to calculate an exact million-dollar unrestricted cash figure.

The 20,867 workbench adjustment includes the issuer's −2,266 “Other” adjustment; the lab does not claim that every part of this unitemized row is noncash. The operating-balance group includes current and non-current balances. Share compensation is added back in the operating-cash presentation, but that does not remove the economic cost to owners. The share reconciliation and cash settlement taxes show separate considerations without automatically deducting the same item twice.

The original cash-flow statement has **no separate FX-effect row**. The three activity totals already reconcile the reported cash change. The workbench receives `fx: "0"` as a clearly labeled worksheet convention, **not a sourced reported zero**. No FX fact is invented in the ledger. This convention does not claim that Apple had no currency exposures or currency effects elsewhere.

The workbench example ID is `apple-2024`; the lab links to `/cash-flow-workbench.html?example=apple-2024`. Its exact cash definition is “Cash, cash equivalents, and restricted cash and cash equivalents.” Copy-ready inputs are decimal strings without grouping commas; capex, dividends and buybacks are positive-use fields, while the reconciliation inputs keep signed values. Reported OCF and reported ending cash are provided as independent comparison totals.

## Validation

`python -m unittest discover -s tests -p test_operating_filing_lab.py -v` exercises independently transcribed Fraction arithmetic against the Decimal generator, all three cash-flow sections, the residual bridge, shares, declared/cash distinctions, units and dates, validation failures, workbench handoff and HTML structure. Rendering is performed in memory by the tests; integration writes generated HTML through the parent build. The HTML has one H1, unique IDs, scoped table headings, captions and native disclosure answers. Browser layout checks belong to the integrated site verification; no browser-rendering claim is made by this module's unit tests.
