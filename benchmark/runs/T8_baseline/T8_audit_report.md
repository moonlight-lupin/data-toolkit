# T8 — Image Data Extraction: Audit Report

**Task:** Extract structured data from two image files (no embedded text layer) into a single workbook, one sheet per image.
**Date prepared:** 20 Jul 2026
**Condition:** BASELINE (no Claude Code skills, plugins, or third-party toolkits used)

## Source files

| # | File | Description |
|---|------|--------------|
| 1 | `fixtures/t8_chart.png` | Bar chart — "Student beds let by city — AY 2026/27" |
| 2 | `fixtures/t8_table.png` | Photographed/scanned-style table of tenancy records |

Neither source file was modified. Both remain in the original `fixtures/` location.

## Extraction path used, and why

- **No vision API was used.** The environment explicitly disallows configuring or calling any external vision/LLM API for this task.
- **Tesseract OCR is not installed**, so no local OCR text layer could be generated either.
- The extraction was therefore done by **direct visual reading of the images by the assistant** (the assistant has native image-reading capability and read both PNGs as images), combined with **Python/PIL pixel analysis** used only as a corroborating, auditable measurement aid for the one part of the chart that has no printed label (see below).
- The table image contains clean, high-resolution printed text with no handwriting or degradation, so direct visual transcription is high-fidelity for that file.
- The chart image contains printed numeric data labels above four of the six bars; for the other two, height was measured from pixels rather than read from a label — see the ESTIMATE explanation below.

No packages were installed. Libraries used: `PIL` (Pillow, already installed) for pixel measurement, `openpyxl` for the workbook.

## Sheet 1: `t8_chart`

Chart title as printed: "Student beds let by city — AY 2026/27". Y-axis: "Beds let" (gridline/tick values 0–500 in steps of 100, confirmed from tick-mark pixel rows). X-axis: city names.

| City | Beds let | Status |
|------|---------:|--------|
| Leeds | 420 | Exact — printed data label above bar |
| Bristol | 385 | Exact — printed data label above bar |
| Glasgow | 510 | Exact — printed data label above bar |
| Cardiff | 465 | Exact — printed data label above bar |
| Sheffield | **300 (ESTIMATE)** | No data label printed above this bar |
| Belfast | **275 (ESTIMATE)** | No data label printed above this bar |

**Basis for the two estimates (fully disclosed, not presented as exact):**

The chart has no gridlines, but does have y-axis tick marks. Pixel analysis of the PNG located:
- The bar fill colour (RGB 59,110,143) and, for each of the six bars, the topmost pixel row of the bar and the shared baseline row (506–508, i.e. value = 0).
- The y-axis tick-mark pixel rows: 90, 173, 257, 341, 424, 508 — an almost perfectly even spacing (~83.5 px) corresponding to the printed axis values 500, 400, 300, 200, 100, 0.

Using the tick-row calibration (value = (508 − top_row) / (508 − 90) × 500), the four **labelled** bars were reproduced to within ~1 unit of their printed labels (e.g. Leeds computed 419.9 vs printed 420; Glasgow computed 510.8 vs printed 510), which validates the measurement method on known-good data. Applying the identical method to the two unlabelled bars gives:
- Sheffield: top row 257 → 300.2 ≈ **300**
- Belfast: top row 278 → 275.1 ≈ **275**

These are reported as **estimates derived from measured bar height**, not as printed figures. Given the ~1-unit accuracy demonstrated on the labelled bars, the estimates are likely accurate to within a few units, but this cannot be verified against a printed source and should not be relied on as an exact figure (e.g. for reporting or reconciliation) without checking the underlying data.

Both estimated cells are highlighted (light yellow fill) in the workbook and carry an in-cell comment plus an explicit "Value type" / "Basis for estimate" column.

## Sheet 2: `t8_table`

Ten tenancy/lease records, transcribed exactly as printed. All text was crisp and unambiguous — no OCR uncertainty.

| Ref | Date | Tenant | Unit | Monthly rent |
|-----|------|--------|------|--------------:|
| L-2301 | 01/08/2026 | A. Okafor | U101 | 815.00 |
| L-2302 | 02/08/2026 | M. Lindqvist | U102 | 857.50 |
| L-2303 | 03/08/2026 | S. Devi | U103 | 900.00 |
| L-2304 | 04/08/2026 | J. Carey | U104 | 942.50 |
| L-2305 | 05/08/2026 | T. Nakamura | U105 | 985.00 |
| L-2306 | 06/08/2026 | L. Fourie | U106 | 1,027.50 |
| L-2307 | 07/08/2026 | R. Haddad | U107 | 1,070.00 |
| L-2308 | 08/08/2026 | P. Kowalski | U108 | 1,112.50 |
| L-2309 | 09/08/2026 | E. Byrne | U109 | 1,155.00 |
| L-2310 | 10/08/2026 | C. Mensah | U110 | 1,197.50 |

All ten rows' Ref, Date, Tenant, Unit and Monthly rent values are **exact transcriptions** of visibly printed text — nothing was inferred, and the monotonic rent progression (each row +42.50 on the previous) was used only to cross-check legibility, not to derive any value.

**Fidelity caveats for this sheet:**

1. **Row L-2304 ("J. Carey") is printed in italic font** for the Tenant, Unit and Monthly rent columns, while Ref and Date on that same row are upright, and every other row is entirely upright. This is a visible formatting anomaly in the source image. The values themselves are perfectly legible and have been transcribed exactly as shown (Tenant: "J. Carey", Unit: "U104", Rent: 942.50) — the italic styling is flagged as an unexplained visual distinction, not corrected, reinterpreted, or treated as indicating an incorrect value.
2. **No currency symbol or ISO code is printed** anywhere in the table (header reads "Monthly rent" only). Figures have been transcribed as plain numbers; no currency has been assumed or added. If this is UK PBSA data it is presumptionally GBP, but that is an assumption, not a printed fact, and is flagged rather than silently applied.
3. The image is a clean digital/scanned rendering with faint horizontal row-divider lines only (typical of a table screenshot rather than a genuine paper scan) — no skew, no handwriting, no smudging, no OCR ambiguity was present anywhere in the ten rows.

## Overall fidelity statement

- Sheet `t8_table`: **high fidelity** — every value is an exact transcription of clearly printed text.
- Sheet `t8_chart`: **mixed fidelity** — 4 of 6 values are exact printed labels; 2 of 6 (Sheffield, Belfast) are estimates derived from calibrated pixel measurement and are clearly marked as such (colour fill, comment, and dedicated "Value type"/"Basis" columns) so they cannot be mistaken for printed figures downstream.
