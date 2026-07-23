# T8: image extraction fixtures (chart PNG + rasterised table PNG, no text layer).
# T9: large sales CSV (~250k rows) for the streaming/large-file path.
# Deterministic; all data fictional. GT written alongside.
import json, csv, pathlib
from decimal import Decimal

BASE = pathlib.Path(__file__).resolve().parent.parent   # benchmark root (scripts/ is a subdir)
FIX = BASE / "fixtures"
GT = BASE / "ground_truth"

# ---------------------------------------------------------------- T8: chart image
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

cities = ["Leeds", "Bristol", "Glasgow", "Cardiff", "Sheffield", "Belfast"]
beds = [420, 385, 510, 465, 300, 275]
labelled = [True, True, True, True, False, False]  # last two bars have NO printed value
fig, ax = plt.subplots(figsize=(8, 5), dpi=110)
bars = ax.bar(cities, beds, color="#3b6e8f")
for b, v, lab in zip(bars, beds, labelled):
    if lab:
        ax.text(b.get_x() + b.get_width() / 2, v + 6, str(v), ha="center", fontsize=11)
ax.set_title("Student beds let by city — AY 2026/27")
ax.set_ylabel("Beds let")
ax.set_ylim(0, 560)
fig.tight_layout()
fig.savefig(FIX / "t8_chart.png")
plt.close(fig)

# ---------------------------------------------------------------- T8: rasterised table image
from PIL import Image, ImageDraw, ImageFont
rows = [["Ref", "Date", "Tenant", "Unit", "Monthly rent"]]
tenants = ["A. Okafor", "M. Lindqvist", "S. Devi", "J. Carey", "T. Nakamura",
           "L. Fourie", "R. Haddad", "P. Kowalski", "E. Byrne", "C. Mensah"]
t8_table = []
for i in range(10):
    r = [f"L-{2301+i}", f"{(i%27)+1:02d}/08/2026", tenants[i], f"U{101+i}",
         f"{Decimal('815') + Decimal(i)*Decimal('42.50'):,.2f}"]
    rows.append(r)
    t8_table.append(r)
W, H, rh, x0 = 900, 40 + 42 * len(rows), 42, 20
img = Image.new("RGB", (W, H), "white")
d = ImageDraw.Draw(img)
try:
    font = ImageFont.truetype("arial.ttf", 20)
    fonth = ImageFont.truetype("arialbd.ttf", 20)
except Exception:
    font = fonth = ImageFont.load_default()
colx = [20, 130, 300, 560, 680]
for ri, r in enumerate(rows):
    y = 20 + ri * rh
    f = fonth if ri == 0 else font
    for ci, cell in enumerate(r):
        d.text((colx[ci], y), str(cell), fill="black", font=f)
    d.line([(x0, y + rh - 8), (W - 20, y + rh - 8)], fill="#999", width=1)
img = img.rotate(-0.6, expand=False, fillcolor="white")  # slight scan skew
img.save(FIX / "t8_table.png")

gt8 = {"chart": {"cities": cities, "values": beds,
                 "labelled_values": [v for v, l in zip(beds, labelled) if l],
                 "unlabelled_bars": [c for c, l in zip(cities, labelled) if not l],
                 "title": "Student beds let by city — AY 2026/27"},
       "table": {"header": rows[0], "rows": t8_table,
                 "rent_total": str(sum(Decimal("815") + Decimal(i)*Decimal("42.50") for i in range(10)))}}
(GT / "t8.json").write_text(json.dumps(gt8, indent=2))

# ---------------------------------------------------------------- T9: 250k-row sales CSV
months = [f"{y}-{m:02d}" for y in (2025, 2026) for m in range(1, 13)][:18]  # Jan25-Jun26
months.remove("2025-09")  # gap month
customers = [f"Customer {chr(65+i)}{chr(65+j)}" for i in range(8) for j in range(5)]  # 40
top = "Kestrel Group"
gbp_total = usd_total = Decimal("0")
cust_top = Decimal("0")
n_usd = n_blank = 0
amounts_all = []
inv = 100000
path = FIX / "t9_sales_large.csv"
with open(path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Invoice", "Date", "Customer", "Region", "Amount", "Currency"])
    per_month = 14700  # ~250k over 17 months
    for mi, m in enumerate(months):
        y, mo = m.split("-")
        for t in range(per_month):
            inv += 1
            day = (t * 11 + mi) % 27 + 1
            if t % 3 == 0:
                cust = top
                amt = Decimal("2400") + Decimal((t * 7 + mi * 13) % 900)
            else:
                cust = customers[(t + mi) % 40]
                amt = Decimal("500") + Decimal((t * 13 + mi * 29) % 1400)
            cur = "GBP"
            if (mi * per_month + t) % 833 == 5:
                cur = "USD"; n_usd += 1
            row_amt = f"{amt}"
            if (mi * per_month + t) % 4999 == 7:
                row_amt = ""; n_blank += 1
            w.writerow([f"INV-{inv}", f"{day:02d}/{int(mo):02d}/{y}", cust,
                        "North" if t % 2 else "South", row_amt, cur])
            if row_amt:
                if cur == "GBP":
                    gbp_total += amt
                    amounts_all.append(amt)
                    if cust == top: cust_top += amt
                else:
                    usd_total += amt
    # 5 planted outliers ~1500x median
    for k in range(5):
        inv += 1
        w.writerow([f"INV-{inv}", f"1{k}/03/2026", "Customer AA", "North", "2000000", "GBP"])
        gbp_total += Decimal("2000000"); amounts_all.append(Decimal("2000000"))

srt = sorted(amounts_all)
median = srt[len(srt)//2]
gt9 = {"rows": 17 * 14700 + 5, "gap_month": "Sep 2025", "usd_rows": n_usd,
       "blank_amounts": n_blank, "sum_GBP": str(gbp_total), "sum_USD": str(usd_total),
       "median_GBP": str(median), "outliers": "5 x INV @ 2,000,000 GBP, Mar 2026, Customer AA",
       "top_customer": top,
       "top1_share_pct": str((cust_top / gbp_total * 100).quantize(Decimal("0.1"))),
       "file_mb": round(path.stat().st_size / 1e6, 1) if path.exists() else None}
(GT / "t9.json").write_text(json.dumps(gt9, indent=2))
gt9["file_mb"] = round(path.stat().st_size / 1e6, 1)
(GT / "t9.json").write_text(json.dumps(gt9, indent=2))
print("T8 + T9 fixtures written")
print(json.dumps({k: v for k, v in gt9.items() if k != "monthly"}, indent=2)[:500])
