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
- **Answer validation** — for `chart` / `table` images the model's answer must contain a
  parseable Markdown table with at least one data row (`validate_description`); other kinds
  only need a non-empty answer (prose is legitimate there). A non-conforming answer triggers
  **one corrective retry** — the retry prompt names the failure and restates the output
  contract (`_corrective_prompt`). An answer that still fails is **kept and flagged**
  (`validation: "flagged: …"`), never dropped and never rewritten. If the corrective
  retry itself fails at transport level, the first answer is likewise kept and flagged
  with the error surfaced, and the uncertain result is **not** cached. `attempts` counts model
  calls; `usage` sums them, so cost accounting stays honest across retries.
- **Cache hygiene rule (apply to any future LLM-backed step in this toolkit):** cache by
  content hash + exact prompt text + model, so a prompt edit invalidates automatically;
  validate the answer before caching; cache flagged answers too (a re-run must not re-bill
  tokens for the same judgement); never cache error results; `--force` bypasses. Reference
  implementation: `image_extract.py` (`validate_description`, `_corrective_prompt`,
  `_merge_usage`, `cache_get` / `cache_put`).
- Transient API failures (429/5xx) retry once inside `call_vision`; permanent failures
  return an error object and are **not** cached.
- Parsed Markdown tables auto-convert comma thousands separators, `%` suffixes, and
  currency symbols via `parse_markdown_table`.
- Optional deps: vision API key + endpoint, `Pillow`, `requests`, `pandas`, `openpyxl`.
  See `README.md#mode--environment-compatibility`.
