"""data-extract — get STRUCTURED data OUT of documents (PDF/scan/Word/email), then hand
to the shared cleanup engine. The counterpart to data-tidy: tidy cleans already-tabular
data; extract locates and pulls data from document-shaped sources —

  - multi-table / multi-page docs  -> list_tables() to pick, get_table() to pull
  - key-value / form / certificate -> extract_fields() (label -> value, one record)
  - scanned docs                   -> via shared ingest's local-OCR fallback

A SHARED module at the toolkit-root scripts/ (with dataclean.py + ingest.py); used by the
data-extract skill and by generated reuse runners (see dataclean.emit_runner). Output +
normalisation + the change report all come from dataclean.

    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path("../../scripts").resolve()))   # shared engine
    import extract
    rec, flags = extract.extract_fields("certificate.pdf", FIELDS)     # form -> one record
    cands = extract.list_tables("report.pdf")                          # which tables exist
    rows  = extract.get_table("report.pdf", page=1, index=0)           # pull one

DATA HANDLING: runs fully local; your data (and any OCR of it) never leaves the machine. See
../DATA-HANDLING.md.
"""

from __future__ import annotations

import re
import sys
import pathlib

try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

# dataclean + ingest live in the same (shared) scripts/ dir as this file
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import dataclean  # noqa: E402
import ingest  # noqa: E402


# --------------------------------------------------------------------------- #
# Key-value / form extraction  ->  one record per document
# --------------------------------------------------------------------------- #
def extract_fields(source, fields, text=None):
    """Pull labelled fields from a document or text into one record.

    fields = [{"name": "Investor", "labels": ["investor", "name of investor"], "type": "text"},
              {"name": "Commitment", "labels": ["commitment", "amount"], "type": "currency",
               "currency": "GBP"},
              {"name": "Close date", "labels": ["close date", "closing"], "type": "date"}]
    Returns (record: {name: value}, flags: [{field, issue}]). Unfound/odd values are flagged,
    never invented. `source` may be a path (read via ingest.read_text) or pass `text=`.
    """
    if text is None:
        text, _ = ingest.read_text(str(source))
    lines = [ln.rstrip() for ln in text.splitlines()]
    record, flags = {}, []
    for f in fields:
        raw = _find_value(lines, f.get("labels", [f["name"]]))
        if raw is None:
            record[f["name"]] = ""
            flags.append({"field": f["name"], "issue": "label not found"})
            continue
        val, note, kept_raw = dataclean._convert(raw, {"type": f.get("type", "text"),
                                                        "currency": f.get("currency"),
                                                        "dayfirst": f.get("dayfirst", True)})
        record[f["name"]] = val
        if note:
            flags.append({"field": f["name"], "issue": note,
                          "value": raw, "kept_raw": kept_raw})
    return record, flags


def _find_value(lines, labels):
    """First value for any label: 'Label: value', 'Label<tab>value', or 'Label   value'."""
    for label in labels:
        lab = re.escape(label.strip())
        for ln in lines:
            m = re.match(rf"\s*{lab}\s*[:\t]\s*(.+)$", ln, re.IGNORECASE) \
                or re.match(rf"\s*{lab}\s{{2,}}(.+)$", ln, re.IGNORECASE)
            if m and m.group(1).strip():
                return m.group(1).strip()
    return None


def fields_to_table(records, field_names):
    """Many per-document records -> (header, rows) for one combined .xlsx."""
    return list(field_names), [[r.get(n, "") for n in field_names] for r in records]


# --------------------------------------------------------------------------- #
# Table selection  ->  pick one of several tables across pages
# --------------------------------------------------------------------------- #
def list_tables(path: str):
    """Enumerate candidate tables in a document -> [{page,index,rows,cols,preview}].
    PDFs via PyMuPDF; .docx via python-docx (page=-1, index=table order)."""
    ext = pathlib.Path(path).suffix.lower()
    if ext == ".pdf":
        return ingest.list_pdf_tables(path)
    if ext == ".docx":
        from docx import Document
        out = []
        for i, tbl in enumerate(Document(path).tables):
            ext_rows = [[c.text for c in row.cells] for row in tbl.rows]
            out.append({"page": -1, "index": i, "rows": len(ext_rows),
                        "cols": max((len(r) for r in ext_rows), default=0),
                        "preview": ext_rows[:2]})
        return out
    return []


def get_table(path: str, page: int = 0, index: int = 0):
    """Pull one specific table (from list_tables coordinates) -> rows."""
    ext = pathlib.Path(path).suffix.lower()
    if ext == ".pdf":
        return ingest.extract_pdf_table(path, page, index)
    if ext == ".docx":
        from docx import Document
        tbl = Document(path).tables[index]
        return [[c.text for c in row.cells] for row in tbl.rows]
    raise ValueError(f"get_table: unsupported type {ext or '(none)'}")


def render_fields_report(records, flags_list):
    """Brief report for a batch of extracted records + their flags."""
    out = [f"# Data-extract report — {len(records)} document(s)"]
    total = sum(len(f) for f in flags_list)
    out.append(f"- Flags across all documents: **{total}** (unfound / verify)")
    for i, flags in enumerate(flags_list):
        if flags:
            out.append(f"\n## ⚑ Document {i + 1}")
            out.append("| Field | Issue | Value |\n|---|---|---|")
            for fl in flags:
                out.append(f"| {fl['field']} | {fl['issue']} | {fl.get('value', '')} |")
    return "\n".join(out)


if __name__ == "__main__":
    FIELDS = [
        {"name": "Investor", "labels": ["investor", "name of investor"], "type": "text"},
        {"name": "Commitment", "labels": ["commitment", "amount"], "type": "currency",
         "currency": "GBP"},
        {"name": "Close date", "labels": ["close date", "closing"], "type": "date"},
        {"name": "Reference", "labels": ["reference", "ref"], "type": "text"},
    ]
    sample = ("ABC Capital — Subscription confirmation\n"
              "Investor: Acme Pension Fund\n"
              "Commitment : GBP 1,000,000\n"
              "Close date\t12/06/2026\n"
              "(no reference quoted)\n")
    rec, flags = extract_fields(None, FIELDS, text=sample)
    print("[extract_fields] record:", rec)
    print("[extract_fields] flags:", flags)
    print()
    print(render_fields_report([rec], [flags]))
