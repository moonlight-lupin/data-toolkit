# Extraction guide — fields, tables, and extract-vs-tidy

## extract vs tidy — which skill?
- **data-tidy** — the input is already roughly tabular (a messy `.xlsx`/CSV, a pasted
  table). You want it cleaned, normalised, validated.
- **data-extract** (this) — the input is a **document** and you need to get data *out*
  of it: a form's labelled fields, or the table(s) buried in a PDF/Word file, or a scan.
- They share the engine: once extracted, rows/records normalise + report identically.
- **Not** deal-document intelligence (lease abstraction, underwriting-model review, comps)
  — that's out of scope. Extract is generic document → structured data, for any function.

## Field list (key-value / form mode)
```json
[
  { "name": "Investor",   "labels": ["investor", "name of investor"], "type": "text" },
  { "name": "Commitment", "labels": ["commitment", "amount"], "type": "currency", "currency": "GBP" },
  { "name": "Close date", "labels": ["close date", "closing"], "type": "date", "dayfirst": true },
  { "name": "Reference",  "labels": ["reference", "ref no", "our ref"], "type": "text" }
]
```
- `labels` — every phrase that might precede the value; first match wins. Add the
  variations you actually see (e.g. "Amount" as well as "Commitment").
- `type` — `text` / `number` / `currency` (+ expected `currency` code) / `date` / `bool`,
  parsed by the shared engine. Output house format: dates DD MMM YYYY, amounts as exact
  `Decimal`, currency amount + code. A bare `$` is ambiguous (give the expected `currency`).
- Matching handles, on the same line, `Label: value`, `Label<tab>value`, `Label   value`
  (2+ spaces) and `Label ..... value` (dotted leader); **and the next-line layout** — a label
  alone on its line with the value on the following line (common on confirmations /
  certificates / boxed forms). The next-line search stops at the *next* field's label, so it
  never grabs a neighbouring label as a value. Case-insensitive. Unfound → blank + flagged;
  ambiguous/odd values → converted-or-kept + flagged.
- Still basic for genuinely 2-D layouts (values in side-by-side boxes / multi-column grids
  that need spatial coordinates) — for those, use **table mode** (`list_tables`/`get_table`)
  or hand the page text to data-tidy.

### Batch (many documents, same shape)
Run `extract_fields` per document, collect the records, then
`fields_to_table(records, field_names)` → one `(header, rows)` → `dataclean.write_xlsx`.
`render_fields_report(records, flags_list)` lists every flag across the batch.

## Table mode
- `list_tables(path)` → candidates `{page, index, engine, rows, cols, preview}` (`.docx` via
  python-docx, `page = -1`). Show them; let the user pick. `engine` says which extractor won
  that page.
- `get_table(path, page, index)` → that table's rows (pass `engine=` to force one). Then treat
  exactly like a tidy source: build a recipe and `dataclean.apply_recipe`.
- **PDF tables use two engines, best result per page:** **pdfplumber** (optional dependency,
  preferred — stronger on messy / borderless / whitespace-aligned tables) and **PyMuPDF**
  (fast, ruled tables, and the OCR backbone for scans). Each page keeps the higher-scoring
  extraction; with pdfplumber not installed it's PyMuPDF only. Install pdfplumber when ruled
  detection is missing columns on borderless tables.
- A PDF that's columnar text with no detectable table still falls back to a text-layout split;
  if even that is poor, use `ingest.read_text` + the tidy text path, or field mode.

## OCR (scanned documents)
- Tried only on pages with no text layer; **local Tesseract** only (never cloud — sensitive data).
- `ingest.ocr_available()` reports readiness; `envcheck.py` probes the binary.
- OCR output is lower-fidelity → always flagged for human review.
- Install (where permitted): Windows `winget install UB-Mannheim.TesseractOCR` (admin /
  IT-deployed). English ships by default; PyMuPDF finds it via PATH + `TESSDATA_PREFIX`.

## Reuse — runner + card (token-saving, verify-first)
**Triage first:** a **one-off / simple** extraction → just deliver the result, don't create
files. Emit a bundle only when the doc type **recurs** or the spec is **complex** (re-deriving
would be costly); ask if borderline. When it's worth it, emit a self-contained **bundle** into
the user's working folder:
```python
dataclean.emit_runner("<working-folder>", "<doctype>", "extract", FIELDS)
# -> extract_<doctype>.py + .md + copies of dataclean/ingest/extract
```
- **`.py`** — bakes the field-spec; imports the engine from its own folder (the copies above),
  so it runs **without the plugin**. `python extract_<doctype>.py <doc...>` = deterministic,
  ~zero-token re-run.
- **`.md` card** — documents the expected source + how to verify.
- **engine copies** — `dataclean.py`/`ingest.py`/`extract.py` live in the working folder beside
  the runner; the folder travels as a unit (e.g. in your synced or shared file store). Regenerating refreshes them.

**On reuse, verify before executing** (layouts drift — a label renamed, a column added):
read the card → inspect the current source → compare → run if it matches, else update the
spec and regenerate. The runner also self-checks and **warns** on missing fields. Keep the
runner + card with the docs (e.g. in your synced or shared file store); they double as a reproducible audit record.
