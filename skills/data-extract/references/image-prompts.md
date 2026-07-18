# Image prompt strategy — vision extraction

Used by `skills/data-extract/scripts/image_extract.py`. Classify the image (filename
hints and/or a light caption), then send the matching prompt to an
**OpenAI-compatible vision endpoint**. Do **not** fall back to Tesseract for chart
data — Tesseract cannot read data points from charts.

| Detected type | Filename / caption hints | Prompt |
|---|---|---|
| **Data chart** (bar / line / pie / scatter) | `chart`, `graph`, `plot`, `bar`, `line`, `pie`, `scatter`, `histogram` | Extract the chart title, axis labels, legend, and every data point value. Output as a Markdown table. Do not round numbers. |
| **Table screenshot** | `table`, `grid`, `spreadsheet`, `ledger`, `screenshot-table` | Extract all table content as a Markdown table. Preserve row/column structure. Do not round numbers. |
| **UI screenshot** | `ui`, `screenshot`, `dashboard`, `mockup`, `wireframe`, `app` | Describe from a frontend developer's perspective: layout, components, text, colours. |
| **Diagram / flowchart** | `diagram`, `flowchart`, `flow`, `uml`, `architecture`, `node` | Describe all nodes and connections (A→B), including branch conditions. |
| **General photo** | *(default)* | Describe the image clearly. If any tabular or numeric data is visible, also output it as a Markdown table. Do not round numbers. |

## Runtime notes

- Images **>5MB** or **>2048px** on the long edge are compressed (Pillow) before the API call.
- Results are cached by `(file hash + prompt hash + model)` under
  `~/.cache/data-toolkit/image_extract/` (override with `--cache-dir`).
- Transient API failures retry once; permanent failures return an error object.
- Parsed Markdown tables auto-convert comma thousands separators, `%` suffixes, and
  currency symbols via `parse_markdown_table`.
- Optional deps: vision API key + endpoint, `Pillow`, `requests`, `pandas`, `openpyxl`.
  See `COMPATIBILITY.md`.
