# Data Toolkit — Mode & Environment Compatibility (pre-screen)

Some skills only run properly in the **right mode / environment** because of how
they're built. **Pre-screen before running a skill** so the user isn't surprised
by a broken or degraded result.

> Referenced by every skill's "Requirements & mode" line. Single source of the
> compatibility rules.

## The two modes

- **Claude Code (local)** — runs on the user's own machine. Can execute the
  bundled Python helpers, read/write the local filesystem, and (on **Windows with
  Microsoft Office** installed) use **Word/Excel via COM** where a skill wants the
  highest-fidelity PDF. **This is the toolkit's primary/intended mode.**
- **Cowork (cloud)** — runs in Anthropic's hosted sandbox. No MS Office / COM
  (PDF would fall back to **LibreOffice**, which can render slightly differently);
  uses its own file paths and **connectors (MCP)** for integrations. Fine for
  portable skills, but the Office-fidelity and local-path assumptions don't all hold.

## How to pre-screen (do this before running a skill)

1. **Know the current mode** — Claude Code (local) vs Cowork (from your runtime/
   system context).
2. **Run the prober:** `python scripts/envcheck.py` — it reports OS, Python libs,
   MS Office-COM vs LibreOffice availability, and the relevant env vars, then prints
   a per-skill readiness line.
3. **Compare to the skill's row below.** If the skill is **blocked or degraded** in
   the current mode, **tell the user up front** and offer the workaround (usually:
   run it in **Claude Code on a Windows machine with Office**, or install a missing
   optional library) — don't just produce a degraded output silently.

## Capability matrix

| Skill | Built for | Hard needs | Degrades / blocks without |
|---|---|---|---|
| data-tidy | any (portable); local processing | Python + `openpyxl` | `PyMuPDF` for PDF input (`pdfplumber` optional — preferred for messy/borderless PDF tables), `python-docx` for .docx, `extract_msg` for .msg (each optional, degrade per-source); **scanned-PDF OCR needs local Tesseract** (digital PDFs/spreadsheets unaffected); **large files (10k+ rows): `pyarrow` + `pandas` optional** — without them `ingest.read_large` falls back to a direct openpyxl read with a warning that large files may OOM |
| data-extract | any (portable); local processing | Python + `PyMuPDF`, `openpyxl` | `pdfplumber` (optional — preferred for messy/borderless PDF tables), `python-docx` for .docx, `extract_msg` for .msg (optional); **scanned-document OCR needs local Tesseract**; **image/chart extraction** (`image_extract.py`) needs a **vision-capable OpenAI-compatible API endpoint + key** plus `Pillow` (resize) and `requests` (optional — degrades by exiting clearly, never silently falls back to Tesseract for chart data); shares the engine at `scripts/` (`dataclean.py`/`ingest.py`/`extract.py`) |
| data-reconcile | any (portable); no network | Python + `openpyxl` (xlsx working paper) | reads CSV/PDF/.docx/.msg via the shared engine (same optional deps as `data-tidy`); no network/Office/connector; produces a working paper (.xlsx) — **never posts**; aggregation (sum-to-one / sum-to-sum) matches are **confirm-first** (the user approves before they count) |
| data-analyse | any (portable); no network | Python + `openpyxl` (xlsx in / metrics workbook out) | reads CSV/PDF/.docx/.msg via the shared engine (same optional deps as `data-tidy`); metric engine (`skills/data-analyse/scripts/analyse.py`) is pure stdlib + `Decimal`; no network/Office/connector; output is an insight brief (`.md`) + optional metrics `.xlsx` — **descriptive analysis, never advice**; **large files (10k+ rows): `pyarrow` + `pandas` optional** — without them `ingest.read_large` falls back to direct read with a warning |
| data-visualise | any (most portable) | Python (stdlib) — pure inline HTML/CSS/SVG, no library to render | `openpyxl` only to read an `.xlsx` source; a desktop browser to `open_in_browser` / print-to-PDF (headless → builds the `.html`, open locally to print); no network/MS Office/creds. **Cowork/Claude.ai:** the output doubles as a **live HTML Artifact** (single-file, dependency-free → renders/edits/shares in the artifact panel as-is). **Claude Code (local):** no artifact panel — open the file in a browser |
| data-convert | any (portable); no network | Python + `openpyxl` (xlsx / template in-out) | reads CSV/PDF/.docx/.msg via the shared engine (same optional deps as `data-tidy`); maps onto a target import **contract** + reshapes (long↔wide, nested JSON↔flat, split, merge); writes CSV/JSON/XLSX/fixed-width or fills a template; delegates cleaning to `data-tidy`; **live inputs (FX) are pinned/user-approved, never engine-fetched**; output is a **draft for review**, never an upload |

**Rule of thumb:** the whole toolkit is **portable and runs on your machine** — pure Python plus
a few optional libraries for non-spreadsheet inputs (PDF/.docx/.msg) and local OCR. None of the
*code* needs the network or credentials. (The AI agent driving it does, of course, send whatever
it reads into its context to your AI provider — see [`DATA-HANDLING.md`](DATA-HANDLING.md).) The
only mode-specific wrinkle is `data-visualise`'s
preview: in a headless/Cowork session it still builds the `.html` (and it doubles as a live
Artifact there) — open it in a desktop browser to print to PDF.

## Not auto-detectable

`envcheck.py` can see installed Python libraries and OS/Office availability, but it **can't**
see whether the current session is headless or has an artifact panel — that depends on the
mode/runtime, not the machine. Confirm that from the runtime context.

## Shared stores & connectors

- **No Microsoft 365 connector is assumed.** The toolkit does not reach a shared file
  store through an M365 MCP.
- **Shared stores are reached as synced local files.** A SharePoint / OneDrive / Drive
  library that syncs into the file system is reached as an ordinary **local path**, not a
  connector. This is why the toolkit is built around local file I/O — and it keeps PII on
  the local/synced store rather than pushing it through a cloud connector. So when a skill
  needs "the shared file", expect a local synced path. See **`DATA-HANDLING.md`**.

## Hooks (data-egress guard + SKILL.md hygiene)

The bundled `hooks/` fire in **Claude Code (local)**, where `${CLAUDE_PLUGIN_ROOT}`
resolves: a PreToolUse **PII-egress reminder** on web / external-connector calls, and a
PostToolUse **SKILL.md hygiene** check. They are **fail-open and self-resolving** — in
**Cowork** (where the plugin root isn't exposed to the hook) they **no-op rather than
block**, and they **never intercept local sandbox tools** (`mcp__workspace__*`,
`mcp__cowork__*`). So in Cowork the egress reminder does not run — **`DATA-HANDLING.md` is
the actual control**, and it applies in **every** mode regardless of the hook.

## Data handling (applies to every skill)

Every skill carries a **`## Data handling`** section pointing to the plugin-root
**`DATA-HANDLING.md`** — the standing PII rule: de-identify / tokenise personal data and
confidential business/financial data before it crosses to any external/third-party tool, keep a local token
map, re-identify locally. It applies in **all modes**.
