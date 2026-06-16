"""Generate synthetic MESSY samples to design/test data-tidy against (no real data
needed). Writes to ../examples/. Each represents a common shape of mess.

    python make_samples.py

Synthetic only — no real data. Use these to exercise the profile -> recipe ->
apply -> report loop; swap in real files later with zero rework.
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

from openpyxl import Workbook

EX = Path(__file__).resolve().parent.parent / "examples"


def finance_export_xlsx():
    """Junk banner rows, messy headers, mixed date + currency formats, blank/totals/dupe."""
    EX.mkdir(exist_ok=True)
    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    data = [
        ["ABC Capital — investor commitments (DRAFT)", "", "", ""],
        ["Generated 13/06/2026", "", "", ""],
        ["CONFIDENTIAL — internal", "", "", ""],
        ["", "", "", ""],
        ["Inv. Name", "Commit", "Close", "Status"],
        ["Acme Pension Fund  ", "£1,000,000", "12/06/2026", "Closed"],
        ["Beta Family Office", "S$ 2.5m", "2026-06-13", "closed"],
        ["acme pension fund", "£1,000,000", "5 Jun 2026", "CLOSED"],     # fuzzy dup
        ["Delta Insurance", "1500000", "45200", "Pending"],             # Excel serial date
        ["Gamma Trust", "not provided", "soon", ""],                    # bad cells
        ["", "", "", ""],                                               # blank
        ["TOTAL", "£4,000,000", "", ""],                               # totals
    ]
    for r in data:
        ws.append(r)
    out = EX / "messy_finance_export.xlsx"
    wb.save(out)
    return out


def contacts_paste_txt():
    """A pasted contact list — inconsistent spacing, 'Last, First', mixed casing."""
    EX.mkdir(exist_ok=True)
    txt = (
        "Name\tEmail\tCompany\tPhone\n"
        "Lee, Jane\tjane.lee@acme.com\tAcme Pension\t+65 6222 0398\n"
        "John Tan\tJOHN.TAN@beta.co\tBeta Family Office\t(65) 9123 4567\n"
        "Lee, Jane\tjane.lee@acme.com\tAcme Pension\t+65 6222 0398\n"   # exact dup
        "Yamamoto Haruki\th.yamamoto@flat.jp\tFlat Collaboration\t03-1234-5678\n"
    )
    out = EX / "messy_contacts.txt"
    out.write_text(txt, encoding="utf-8")
    return out


def sample_table_pdf():
    """A small DIGITAL pdf with a table (exercises the PyMuPDF table path, not OCR)."""
    try:
        import fitz
    except ImportError:
        return None
    EX.mkdir(exist_ok=True)
    doc = fitz.open()
    page = doc.new_page()
    text = ("Investor            Commitment      Close\n"
            "Acme Pension        GBP 1,000,000   12 Jun 2026\n"
            "Beta Family Office  SGD 2,500,000   13 Jun 2026\n")
    page.insert_text((50, 80), text, fontsize=11, fontname="cour")
    out = EX / "sample_table.pdf"
    doc.save(out)
    return out


if __name__ == "__main__":
    print("wrote:", finance_export_xlsx())
    print("wrote:", contacts_paste_txt())
    pdf = sample_table_pdf()
    print("wrote:", pdf if pdf else "(PDF skipped — PyMuPDF not installed)")
