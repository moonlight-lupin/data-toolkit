# T6 scaling fixtures: bank vs cashbook reconciliation at 5,000 and 20,000 rows.
# Same trap taxonomy as T3, scaled. Deterministic. All data fictional.
import json, pathlib
from datetime import date, timedelta
from decimal import Decimal
import openpyxl

BASE = pathlib.Path(__file__).resolve().parent.parent   # benchmark/ root (scripts live in scripts/)
FIX = BASE / "fixtures"
GT = BASE / "ground_truth"

def dstr(d): return d.strftime("%d/%m/%Y")

def build(tag, n_exact, n_timing, n_amb, n_sign, n_dup, n_bank_only, n_cash_only, n_gst):
    start = date(2026, 1, 5)
    bank, cash = [], []
    ref = 10000
    # exact matches — unique amounts, dates spread over ~150 days
    for i in range(n_exact):
        amt = Decimal("100.00") + Decimal(i) * Decimal("0.73")
        d = start + timedelta(days=i % 150)
        sign = 1 if i % 3 else -1
        desc = f"TRF {'IN' if sign > 0 else 'OUT'} REF{ref+i}"
        bank.append([dstr(d), desc, "" if sign > 0 else str(amt), str(amt) if sign > 0 else ""])
        cash.append([dstr(d), f"CB-{ref+i}", desc, str(sign * amt)])
    # timing differences (3-5 day gaps, unique amount range 700000+)
    for j in range(n_timing):
        amt = Decimal("700000") + Decimal(j) * Decimal("1.11")
        d = start + timedelta(days=j % 140)
        bank.append([dstr(d + timedelta(days=3 + j % 3)), f"CHQ 9{j:03d} CLEARED", str(amt), ""])
        cash.append([dstr(d), f"CB-T{j:04d}", f"Cheque 9{j:03d} supplier", str(-amt)])
    # ambiguous (8-15 day gaps, range 710000+)
    for j in range(n_amb):
        amt = Decimal("710000") + Decimal(j) * Decimal("2.17")
        d = start + timedelta(days=10 + j % 120)
        bank.append([dstr(d + timedelta(days=8 + j % 8)), f"FAST PAYMENT AMB{j:03d}", "", str(amt)])
        cash.append([dstr(d), f"CB-A{j:04d}", f"Receipt AMB{j:03d}", str(amt)])
    # sign flips (range 720000+): bank debit, cashbook wrongly positive, same date
    for j in range(n_sign):
        amt = Decimal("720000") + Decimal(j) * Decimal("3.31")
        d = start + timedelta(days=20 + j % 100)
        bank.append([dstr(d), f"DD POLICY S{j:03d}", str(amt), ""])
        cash.append([dstr(d), f"CB-S{j:04d}", f"Policy S{j:03d}", str(amt)])
    # duplicates in cashbook (range 730000+): matched pair + extra cashbook copy
    for j in range(n_dup):
        amt = Decimal("730000") + Decimal(j) * Decimal("4.43")
        d = start + timedelta(days=30 + j % 90)
        desc = f"TRF IN REF D{j:03d}"
        bank.append([dstr(d), desc, "", str(amt)])
        cash.append([dstr(d), f"CB-D{j:04d}", desc, str(amt)])
        cash.append([dstr(d), f"CB-D{j:04d}X", desc + " (entered again)", str(amt)])
    # bank-only (range 740000+)
    for j in range(n_bank_only):
        amt = Decimal("740000") + Decimal(j) * Decimal("5.57")
        bank.append([dstr(start + timedelta(days=40 + j % 80)), f"BANK FEE B{j:03d}", str(amt), ""])
    # cashbook-only (range 750000+)
    for j in range(n_cash_only):
        amt = Decimal("750000") + Decimal(j) * Decimal("6.61")
        cash.append([dstr(start + timedelta(days=50 + j % 70)), f"CB-U{j:04d}",
                     f"Unpresented item U{j:03d}", str(-amt)])
    # GST amount mismatches (range 760000+): cash net, bank gross = net*1.09, same date
    for j in range(n_gst):
        net = Decimal("760000") + Decimal(j) * Decimal("100")
        gross = (net * Decimal("1.09")).quantize(Decimal("0.01"))
        d = start + timedelta(days=60 + j % 60)
        bank.append([dstr(d), f"PAYMENT VENDOR G{j:03d}", str(gross), ""])
        cash.append([dstr(d), f"CB-G{j:04d}", f"Vendor G{j:03d} net of GST", str(-net)])

    with open(FIX / f"t6{tag}_bank_statement.csv", "w", encoding="utf-8") as f:
        f.write("Date,Description,Debit,Credit\n")
        for r in bank: f.write(",".join(r) + "\n")
    wb = openpyxl.Workbook(write_only=True)
    ws = wb.create_sheet("Cashbook")
    ws.append(["Date", "Ref", "Details", "Amount"])
    for r in cash: ws.append([r[0], r[1], r[2], float(r[3])])
    wb.save(FIX / f"t6{tag}_cashbook.xlsx")
    gt = {"exact_matches": n_exact + n_dup,  # dup base pairs also match 1:1
          "timing_difference": n_timing, "ambiguous_beyond_window": n_amb,
          "sign_flip": n_sign, "duplicate_in_cashbook": n_dup,
          "bank_only": n_bank_only, "cashbook_only": n_cash_only,
          "amount_mismatch_gst": n_gst,
          "bank_rows": len(bank), "cashbook_rows": len(cash)}
    (GT / f"t6{tag}.json").write_text(json.dumps(gt, indent=2))
    print(tag, "bank", len(bank), "cash", len(cash))

# medium: ~5,000 cashbook rows; large: ~20,000
build("m", n_exact=4900, n_timing=20, n_amb=5, n_sign=5, n_dup=10,
      n_bank_only=15, n_cash_only=15, n_gst=5)
build("l", n_exact=19860, n_timing=40, n_amb=10, n_sign=10, n_dup=20,
      n_bank_only=20, n_cash_only=20, n_gst=10)
