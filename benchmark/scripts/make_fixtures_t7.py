# T7 conversion fixtures: monthly GL exports to be converted to a journal-import contract.
# Jun = initial build; Jul = clean repeat (same shape); Aug = drifted (renamed column,
# new column, one blank required Account Code). Deterministic; all data fictional.
import json, pathlib
from decimal import Decimal
import openpyxl

BASE = pathlib.Path(__file__).resolve().parent.parent   # benchmark root (scripts/ is a subdir)
FIX = BASE / "fixtures"
GT = BASE / "ground_truth"

ACCTS = [("1000", "Cash at bank"), ("1200", "Trade debtors"), ("2000", "Trade creditors"),
         ("4000", "Sales revenue"), ("5000", "Cost of sales"), ("6100", "Rent expense"),
         ("6200", "Salaries"), ("7300", "Office costs")]
CCS = ["CC-100", "CC-200", "CC-300", "CC-400", "CC-500"]

def build(tag, month, n_pairs, drift=False):
    hdr = ["Entry No", "Posting Date", "Account Code", "Account Name",
           "Description", "Debit", "Credit", "CC Code" if drift else "Cost Centre"]
    if drift:
        hdr.append("Approved By")
    rows, gross = [], Decimal("0")
    eno = {"06": 9000, "07": 9500, "08": 9950}[month]
    for i in range(n_pairs):
        amt = Decimal("250.00") + Decimal(i) * Decimal("13.57")
        gross += amt
        day = (i % 28) + 1
        d = f"{day:02d}/{month}/2026"
        da, ca = ACCTS[i % 8], ACCTS[(i + 3) % 8]
        cc = CCS[i % 5]
        desc = f"Journal {month}-{i:03d}"
        r1 = [f"E{eno + 2*i}", d, da[0], da[1], desc, str(amt), "", cc]
        r2 = [f"E{eno + 2*i + 1}", d, ca[0], ca[1], desc, "", str(amt), cc]
        if drift:
            r1.append("J Ellis"); r2.append("J Ellis")
        rows.append(r1); rows.append(r2)
    if drift:  # one row with blank required Account Code
        rows[10][2] = ""
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = "GL Export"
    ws.append(hdr)
    for r in rows: ws.append(r)
    wb.save(FIX / f"t7_gl_{tag}.xlsx")
    return {"rows": len(rows), "gross_debits": str(gross), "net": "0.00",
            "first_entry": rows[0][0], "last_entry": rows[-1][0]}

gt = {"contract": {
        "columns": ["JournalRef", "Date", "AccountCode", "Narrative", "Amount", "CostCentre", "Source"],
        "date_format": "YYYY-MM-DD", "amount": "signed, debit positive, 2dp",
        "source_constant": "GLEXPORT", "required": ["JournalRef", "Date", "AccountCode", "Amount"]},
      "jun": build("jun", "06", 60),
      "jul": build("jul", "07", 59),
      "aug": build("aug", "08", 57, drift=True)}
gt["aug"]["drift"] = ["'Cost Centre' renamed to 'CC Code'", "new column 'Approved By'",
                      "one row (11th data row) has blank Account Code (required)"]
(GT / "t7.json").write_text(json.dumps(gt, indent=2))
print(json.dumps(gt, indent=2)[:600])
