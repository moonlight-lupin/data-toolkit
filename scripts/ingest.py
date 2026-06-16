"""Shared ingest adapters — turn ANY source into a raw table (list of rows) or plain
text, so the diversity of inputs lives here and the cleanup pipeline (dataclean.py) stays one
shared path. Used by `data-tidy` (clean tabular data) and `data-extract` (get data
out of documents). Lives at the toolkit-root `scripts/`; skills import it by adding
`../../scripts` to sys.path (run from the skill directory).

    from ingest import read_any, read_paste, read_text, list_pdf_tables, ocr_available
    rows, note = read_any("export.xlsx")      # or .csv/.tsv, a .pdf, a .docx, a .msg
    rows, note = read_paste(pasted_text)       # markdown / tab / csv-ish pasted table
    text, note = read_text("form.pdf")         # document -> plain text (OCR fallback)
    cands      = list_pdf_tables("report.pdf") # enumerate tables per page for selection

Heavy deps (PyMuPDF, python-docx, extract_msg, Tesseract) are imported LAZILY and degrade
with a clear message rather than crashing — most jobs (xlsx / csv / paste / digital PDF)
need none of them.

OCR (scanned PDFs): tried ONLY when a PDF page has no text layer, and ONLY via LOCAL
Tesseract — never a cloud OCR (the Data Toolkit runs fully local; your data never leaves
the machine). OCR'd rows are lower-fidelity; the caller flags them for review.
"""

from __future__ import annotations

import csv
import io
import shutil
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass


def read_any(path: str):
    """Dispatch on extension -> (rows, note)."""
    ext = Path(path).suffix.lower()
    if ext in (".xlsx", ".xlsm"):
        return read_xlsx(path)
    if ext in (".csv", ".tsv", ".txt"):
        return read_csv(path)
    if ext == ".pdf":
        return read_pdf(path)
    if ext in (".docx",):
        return read_docx(path)
    if ext == ".msg":
        return read_msg(path)
    raise ValueError(f"Unsupported source type: {ext or '(no extension)'}")


def read_xlsx(path: str, sheet=None):
    from openpyxl import load_workbook
    wb = load_workbook(path, data_only=True, read_only=True)
    ws = wb[sheet] if sheet else wb.active
    rows = [["" if c is None else c for c in row]
            for row in ws.iter_rows(values_only=True)]
    return rows, f"xlsx '{ws.title}', {len(rows)} raw rows"


def read_csv(path: str):
    with open(path, "r", encoding="utf-8-sig", errors="replace", newline="") as f:
        sample = f.read(4096)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
        except csv.Error:
            dialect = csv.excel
        rows = [list(r) for r in csv.reader(f, dialect)]
    return rows, f"delimited text, {len(rows)} raw rows"


def read_paste(text: str):
    """Parse a pasted table: markdown pipe-table, else tab/multi-space/CSV-ish lines."""
    lines = [ln for ln in text.splitlines() if ln.strip() != ""]
    if not lines:
        return [], "empty paste"
    if all("|" in ln for ln in lines[:3]):  # markdown table
        rows = []
        for ln in lines:
            if set(ln.strip()) <= set("|-: "):  # separator row
                continue
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            rows.append(cells)
        return rows, f"pasted markdown table, {len(rows)} rows"
    if "\t" in text:
        return [ln.split("\t") for ln in lines], f"pasted TSV, {len(lines)} rows"
    try:
        rows = [list(r) for r in csv.reader(io.StringIO(text))]
        if max(len(r) for r in rows) > 1:
            return rows, f"pasted CSV, {len(rows)} rows"
    except csv.Error:
        pass
    import re
    return [re.split(r"\s{2,}", ln.strip()) for ln in lines], f"pasted (split on 2+ spaces), {len(lines)} rows"


def read_pdf(path: str):
    """Digital PDF tables via PyMuPDF; OCR fallback (local Tesseract) for scanned pages."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return [], "PyMuPDF (fitz) not installed — cannot read PDF"
    import re
    rows, ocr_pages, scanned, text_pages = [], 0, 0, 0
    doc = fitz.open(path)
    for page in doc:
        found = False
        try:
            for tbl in page.find_tables().tables:  # ruled / aligned tables — best structure
                ext = tbl.extract()
                if ext:
                    rows.extend([["" if c is None else c for c in r] for r in ext])
                    found = True
        except Exception:  # noqa: BLE001 — find_tables can be brittle on odd PDFs
            pass
        if found:
            continue
        text = page.get_text("text")
        if text.strip():                          # digital, columnar text but no ruled table
            rows.extend([re.split(r"\s{2,}", ln.strip()) for ln in text.splitlines() if ln.strip()])
            text_pages += 1
        else:                                     # no text layer -> likely scanned
            scanned += 1
            ocr_rows = _ocr_page(page)
            if ocr_rows:
                rows.extend(ocr_rows)
                ocr_pages += 1
    note = f"PDF, {len(rows)} rows"
    if text_pages:
        note += f"; {text_pages} page(s) via text-layout split (check column alignment)"
    if scanned:
        note += (f"; {ocr_pages}/{scanned} scanned page(s) OCR'd (LOWER FIDELITY — review)"
                 if ocr_pages else f"; {scanned} scanned page(s) need OCR — Tesseract not available")
    return rows, note


def _ocr_page(page):
    """OCR one PyMuPDF page via local Tesseract, returning whitespace-split rows. [] if no engine."""
    if not ocr_available():
        return []
    try:
        tp = page.get_textpage_ocr(flags=0, full=True)  # uses local Tesseract
        text = page.get_text("text", textpage=tp)
    except Exception:  # noqa: BLE001
        return []
    import re
    return [re.split(r"\s{2,}", ln.strip()) for ln in text.splitlines() if ln.strip()]


def ocr_available() -> bool:
    """Local Tesseract present? (binary on PATH + PyMuPDF OCR support). Cloud OCR is never used."""
    if not shutil.which("tesseract"):
        return False
    try:
        import fitz  # noqa: F401
        return hasattr(fitz.Page, "get_textpage_ocr")
    except ImportError:
        return False


def read_docx(path: str):
    try:
        from docx import Document
    except ImportError:
        return [], "python-docx not installed — cannot read .docx tables"
    rows = []
    for tbl in Document(path).tables:
        for row in tbl.rows:
            rows.append([c.text for c in row.cells])
    return rows, f"docx, {len(rows)} table rows from {len(Document(path).tables)} table(s)"


def read_msg(path: str):
    try:
        import extract_msg
    except ImportError:
        return [], "extract_msg not installed — cannot read Outlook .msg"
    body = extract_msg.Message(path).body or ""
    return read_paste(body)[0], "Outlook .msg body parsed as a pasted table"


# --------------------------------------------------------------------------- #
# Document -> plain text + table enumeration (for data-extract: key-value
# field extraction and multi-table selection)
# --------------------------------------------------------------------------- #
def read_text(path: str):
    """Whole-document plain text -> (text, note). PDF uses the text layer with a local-OCR
    fallback for scanned pages; .docx joins paragraphs + table cells; .msg the body; .txt raw."""
    ext = Path(path).suffix.lower()
    if ext == ".pdf":
        try:
            import fitz
        except ImportError:
            return "", "PyMuPDF (fitz) not installed — cannot read PDF text"
        parts, ocr_pages, scanned = [], 0, 0
        for page in fitz.open(path):
            t = page.get_text("text")
            if t.strip():
                parts.append(t)
            elif ocr_available():
                try:
                    tp = page.get_textpage_ocr(flags=0, full=True)
                    parts.append(page.get_text("text", textpage=tp))
                    ocr_pages += 1
                except Exception:  # noqa: BLE001
                    scanned += 1
            else:
                scanned += 1
        note = "PDF text"
        if ocr_pages:
            note += f"; {ocr_pages} page(s) OCR'd (review)"
        if scanned:
            note += f"; {scanned} scanned page(s) unreadable (no Tesseract)"
        return "\n".join(parts), note
    if ext == ".docx":
        try:
            from docx import Document
        except ImportError:
            return "", "python-docx not installed"
        doc = Document(path)
        lines = [p.text for p in doc.paragraphs]
        for tbl in doc.tables:
            for row in tbl.rows:
                lines.append("\t".join(c.text for c in row.cells))
        return "\n".join(lines), "docx text"
    if ext == ".msg":
        try:
            import extract_msg
        except ImportError:
            return "", "extract_msg not installed"
        return (extract_msg.Message(path).body or ""), "msg body"
    if ext in (".txt", ".csv", ".tsv"):
        return Path(path).read_text(encoding="utf-8-sig", errors="replace"), "text file"
    raise ValueError(f"read_text: unsupported type {ext or '(none)'}")


def list_pdf_tables(path: str):
    """Enumerate tables per page -> [{page, index, rows, cols, preview}] so the caller can
    pick which to extract (multi-table / multi-page documents)."""
    try:
        import fitz
    except ImportError:
        return []
    out = []
    for pno, page in enumerate(fitz.open(path)):
        try:
            tables = page.find_tables().tables
        except Exception:  # noqa: BLE001
            tables = []
        for i, tbl in enumerate(tables):
            ext = tbl.extract()
            if not ext:
                continue
            out.append({"page": pno, "index": i, "rows": len(ext),
                        "cols": max(len(r) for r in ext),
                        "preview": [["" if c is None else c for c in r] for r in ext[:2]]})
    return out


def extract_pdf_table(path: str, page: int, index: int = 0):
    """Pull one specific table (by page + index from list_pdf_tables) -> rows."""
    import fitz
    tbl = fitz.open(path)[page].find_tables().tables[index]
    return [["" if c is None else c for c in r] for r in tbl.extract()]


if __name__ == "__main__":
    paste = "Investor | Commit | Close\nAcme Pension | £1,000,000 | 12/06/2026\nBeta FO | S$2.5m | 2026-06-13"
    rows, note = read_paste(paste)
    print("[paste]", note)
    for r in rows:
        print("  ", r)
    print("[ocr] local Tesseract available:", ocr_available())
