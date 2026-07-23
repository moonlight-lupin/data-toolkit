# T8 — Image Data Extraction: Audit Report

**Date:** 20 Jul 2026
**Skill used:** `data-extract` (image-inputs path)
**Output workbook:** `T8_extracted.xlsx` (sheets: `t8_chart`, `t8_table`)

## Extraction path actually used, and why

The skill's documented path for chart/table **image** inputs is
`skills/data-extract/scripts/image_extract.py`, which calls an external
OpenAI-compatible **vision API** (`VISION_API_KEY` / `OPENAI_API_KEY`). Per the
environment constraint for this task, **no such key is configured and none may
be set up** (organisation policy: no document content to external APIs).

`image_extract.py` was checked and confirmed to fail closed as designed — with
no key present it returns an explicit error (`"No vision API key configured...
Will not fall back to Tesseract for chart/image data."`) rather than silently
degrading. It was **not run** against these two images, consistent with that
design and with the organisation's no-external-API constraint.

**Tesseract** (local OCR) is also not installed in this environment, and would
not have helped regardless: the skill explicitly notes Tesseract cannot read
chart data points, and OCR of the table image would only extract raw text
without any confidence check on numbers — no better and less auditable than
the path actually used.

**Path used instead:** the two images were viewed directly by the AI agent
driving this session (native multimodal reading, via the `Read` tool), which
is the same AI provider already processing this conversation — not a
third-party or external tool. This keeps the images off any external service,
consistent with the skill's data-handling rule (never send to an *external or
third-party* tool without explicit choice).

For the chart, visible transcription was supplemented with a **local, offline
pixel-measurement check** (Python/Pillow, run on this machine only) to convert
un-labelled bar heights to values, rather than eyeballing them — see below.
No image content or data left the local machine at any point.

**Fidelity of this path:** equivalent to careful manual transcription by a
person looking at the image. It is not a certified OCR/vision output and
carries the same residual risk as any manual reading (e.g. font ambiguity) —
flagged per item below. This is a **draft extraction for review**, not a
certified dataset.

---

## Sheet 1 — `t8_chart` (source: `t8_chart.png`)

Chart type: vertical bar chart. Title (as printed): **"Student beds let by
city — AY 2026/27"**. Y-axis label: **"Beds let"**. Single series, no legend.
X-axis categories, left to right: Leeds, Bristol, Glasgow, Cardiff, Sheffield,
Belfast.

| City | Beds let | Basis |
|---|---|---|
| Leeds | 420 | **Exact** — printed above the bar |
| Bristol | 385 | **Exact** — printed above the bar |
| Glasgow | 510 | **Exact** — printed above the bar |
| Cardiff | 465 | **Exact** — printed above the bar |
| Sheffield | **300** | **ESTIMATE** — no data label printed above this bar |
| Belfast | **275** | **ESTIMATE** — no data label printed above this bar |

**How the two estimates were derived (workings, so they can be checked):**
Four of the six bars carry a printed value. The other two (Sheffield, Belfast)
do not. Rather than eyeballing the bar height against the y-axis, a pixel
measurement was taken locally (Pillow) for all six bars:

- Bar pixel-heights (baseline to top of fill): Leeds 349px, Bristol 320px,
  Glasgow 425px, Cardiff 387px, Sheffield 249px, Belfast 228px.
- Using the four **known** values as calibration: 420/349 = 1.2034,
  385/320 = 1.2031, 510/425 = 1.2000, 465/387 = 1.2016 units/pixel — very
  consistent (spread of ~0.003), average **1.2020 units/px**.
- Applying that scale: Sheffield 249px → 299.3 → rounded to **300**;
  Belfast 228px → 274.1 → rounded to **275**.

These two figures are **estimates**, not printed values, and are marked
`ESTIMATE` (with amber fill) in the workbook. They should not be relied on as
exact bed counts without confirming against the underlying data used to build
the chart.

---

## Sheet 2 — `t8_table` (source: `t8_table.png`)

A 10-row schedule, columns: Ref, Date, Tenant, Unit, Monthly rent. All 50
data values (10 rows × 5 columns) are **printed explicitly** in the image and
were transcribed exactly as shown — no estimation required for this sheet.

| Ref | Date | Tenant | Unit | Monthly rent (as printed) |
|---|---|---|---|---|
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

**Fidelity caveats (flagged, none change the transcribed values):**
1. **No currency symbol or ISO code is printed anywhere in the image.**
   Figures are transcribed as bare numbers exactly as shown. Per house style
   (show currency with its symbol/code where ambiguous) this should be
   confirmed against the source document/system before use — do **not**
   assume GBP/£ purely because this is a UK PBSA context; that would be an
   invented fact, not a transcribed one. Flagged in the workbook (column
   header note) rather than silently assumed.
2. **Row L-2304 (J. Carey / U104 / 942.50) is rendered in italic in the
   source image**, unlike every other row. No legend or footnote in the image
   explains this formatting. It is transcribed with the same value as printed
   and flagged in the workbook — the italics may indicate an amendment,
   a pending item, or simply an incidental rendering artefact of the scan;
   this cannot be determined from the image alone.
3. Dates are transcribed exactly as printed (DD/MM/YYYY, e.g. `01/08/2026`)
   rather than reformatted to house style (DD MMM YYYY), since reformatting
   a scanned/photographed source risks silently changing an ambiguous
   DD/MM vs MM/DD reading. Recommend confirming the format with the source
   before any downstream use; flagged for reviewer attention.

---

## Overall

- No values were invented. Every figure in `t8_table` and 4 of 6 in
  `t8_chart` are exact, printed transcriptions. The 2 remaining chart values
  are clearly marked `ESTIMATE` with their derivation shown, not presented as
  exact.
- No document content or image data was sent to any external or third-party
  service; no vision API key was configured, requested, or required.
- **Human-in-the-loop**: this is a draft extraction for review — please
  verify the two Sheffield/Belfast estimates and the currency assumption
  before relying on these figures.
