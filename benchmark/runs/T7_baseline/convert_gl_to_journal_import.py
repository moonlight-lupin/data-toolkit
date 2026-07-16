#!/usr/bin/env python3
"""
convert_gl_to_journal_import.py
================================

REUSABLE MONTHLY CONVERSION ARTEFACT (Task T7 — GL export -> journal import)

Purpose
-------
Converts the monthly GL export (system A) into the downstream accounting
system's journal import CSV format (system B). Built to be run by an agent
or analyst who has NOT seen the original conversation -- everything needed
is documented below.

STANDING RULE (do not skip, every month, no exceptions)
---------------------------------------------------------
Each month's source file must be SENSE-CHECKED against the expected shape
BEFORE converting. Any discrepancy versus the expected shape --
  * a renamed, missing, or unexpected/new column,
  * a required output field that would come out empty,
  * a row where Debit and Credit are both populated or both blank,
  * a non-numeric Debit/Credit value, or a Posting Date not in DD/MM/YYYY,
-- must be FLAGGED and that row (or the whole run, for a structural/column
problem) must be EXCLUDED / STOPPED rather than silently converted or
guessed. Never invent or infer a missing value. When in doubt, exclude
and flag; do not guess.

Source (system A) expected shape
---------------------------------
.xlsx, single sheet, header row with EXACTLY these columns (order not
required, but names must match -- case-sensitive):
    Entry No, Posting Date, Account Code, Account Name, Description,
    Debit, Credit, Cost Centre
Posting Date is text in DD/MM/YYYY format.
Debit/Credit: for each row, exactly ONE of the two should be populated
(the other blank/None) -- a normal single-sided GL export line.

Target (system B) contract -- journal import CSV
--------------------------------------------------
UTF-8 CSV, header row, columns in this EXACT order:
    JournalRef, Date, AccountCode, Narrative, Amount, CostCentre, Source
Mapping:
    JournalRef  = Entry No
    Date        = Posting Date, re-expressed as YYYY-MM-DD
    AccountCode = Account Code
    Narrative   = Description
    Amount      = signed, 2 d.p. = Debit - Credit (debit positive, credit negative)
    CostCentre  = Cost Centre
    Source      = constant string "GLEXPORT"
Required fields (must never be empty in the OUTPUT): JournalRef, Date,
AccountCode, Amount. A row failing any required field is flagged and
EXCLUDED from the CSV -- never guessed or defaulted.

Usage
-----
    python convert_gl_to_journal_import.py <source.xlsx> <output.csv>

Example (July 2026 leg):
    python convert_gl_to_journal_import.py fixtures/t7_gl_jul.xlsx runs_t7_sonnet/T7_base/journal_import_jul2026.csv

The script prints a summary (rows in/out, total Amount, any flagged rows)
to stdout, and ALSO writes a sibling "<output>.exceptions.log" file
listing every flagged/excluded row and reason, if any exist. If a
structural problem is found (missing/renamed/extra expected column), the
script STOPS before converting anything and prints/writes what's wrong --
it does not attempt a partial or best-guess conversion.

Requires only openpyxl (standard in this environment). No third-party
toolkits or Claude Code skills are used or required by this script.
"""

import csv
import sys
from datetime import datetime
from decimal import Decimal, InvalidOperation

import openpyxl

# ---------------------------------------------------------------------------
# Expected source shape -- edit ONLY if the source system's export genuinely
# and permanently changes (and note the change + date below).
# ---------------------------------------------------------------------------
EXPECTED_SOURCE_COLUMNS = [
    "Entry No",
    "Posting Date",
    "Account Code",
    "Account Name",
    "Description",
    "Debit",
    "Credit",
    "Cost Centre",
]

OUTPUT_HEADER = [
    "JournalRef",
    "Date",
    "AccountCode",
    "Narrative",
    "Amount",
    "CostCentre",
    "Source",
]

SOURCE_CONSTANT = "GLEXPORT"


class SchemaError(Exception):
    """Raised when the source file's shape does not match what's expected.
    On this error the script must STOP -- no partial/guessed conversion."""


def load_source_rows(path):
    """Load the source workbook and return (header, list-of-row-tuples)."""
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.active
    all_rows = list(ws.iter_rows(values_only=True))
    if not all_rows:
        raise SchemaError(f"Source file '{path}' appears to be empty (no rows).")
    header = [str(h).strip() if h is not None else h for h in all_rows[0]]
    data_rows = all_rows[1:]
    return header, data_rows


def sense_check_header(header, source_path):
    """
    Standing rule: sense-check the header against the expected shape
    BEFORE converting anything. Flags:
      - missing expected column
      - renamed / unexpected column names
      - column order is NOT enforced (only names/presence), since the
        contract only fixes the OUTPUT column order, not the input's.
    """
    problems = []
    header_set = set(header)
    expected_set = set(EXPECTED_SOURCE_COLUMNS)

    missing = [c for c in EXPECTED_SOURCE_COLUMNS if c not in header_set]
    extra = [c for c in header if c not in expected_set]

    if missing:
        problems.append(f"Missing expected column(s): {missing}")
    if extra:
        problems.append(
            f"Unexpected/new/renamed column(s) present: {extra} "
            f"(if this is a genuine new column from the source system, "
            f"a human must confirm it before this script is updated)"
        )

    if problems:
        raise SchemaError(
            f"Source file '{source_path}' header does not match the expected "
            f"shape. STOPPING -- no rows converted.\n"
            + "\n".join(f"  - {p}" for p in problems)
            + f"\n  Expected columns: {EXPECTED_SOURCE_COLUMNS}\n"
            + f"  Found columns:    {header}"
        )


def is_blank(v):
    return v is None or (isinstance(v, str) and v.strip() == "")


def parse_date_ddmmyyyy(v):
    """Parse a DD/MM/YYYY string; return None if it doesn't parse."""
    if is_blank(v):
        return None
    try:
        return datetime.strptime(str(v).strip(), "%d/%m/%Y").date()
    except ValueError:
        return None


def parse_decimal(v):
    """Parse a numeric (string or number) cell to Decimal; None if blank/invalid."""
    if is_blank(v):
        return None
    try:
        return Decimal(str(v).strip())
    except InvalidOperation:
        return None


def convert(source_path, output_path):
    header, data_rows = load_source_rows(source_path)
    sense_check_header(header, source_path)

    col_idx = {name: header.index(name) for name in EXPECTED_SOURCE_COLUMNS}

    out_rows = []
    flagged = []  # (row_number_in_source, entry_no, reason)
    total_amount = Decimal("0.00")

    for i, row in enumerate(data_rows, start=2):  # row 1 is header
        def get(col):
            idx = col_idx[col]
            return row[idx] if idx < len(row) else None

        entry_no = get("Entry No")
        posting_date_raw = get("Posting Date")
        account_code = get("Account Code")
        description = get("Description")
        debit_raw = get("Debit")
        credit_raw = get("Credit")
        cost_centre = get("Cost Centre")

        row_problems = []

        # --- structural sense-checks on this row (debit/credit shape) ---
        debit = parse_decimal(debit_raw)
        credit = parse_decimal(credit_raw)

        if debit_raw is not None and not is_blank(debit_raw) and debit is None:
            row_problems.append(f"Debit value '{debit_raw}' is not numeric")
        if credit_raw is not None and not is_blank(credit_raw) and credit is None:
            row_problems.append(f"Credit value '{credit_raw}' is not numeric")

        debit_present = debit is not None
        credit_present = credit is not None
        if debit_present and credit_present:
            row_problems.append("both Debit and Credit are populated (expected exactly one)")
        if not debit_present and not credit_present:
            row_problems.append("both Debit and Credit are blank (expected exactly one)")

        # --- date ---
        posting_date = parse_date_ddmmyyyy(posting_date_raw)
        if posting_date is None:
            row_problems.append(f"Posting Date '{posting_date_raw}' is not a valid DD/MM/YYYY date")

        # --- compute Amount only if debit/credit shape is sane ---
        amount = None
        if not row_problems or all(
            "Debit" not in p and "Credit" not in p and "both" not in p for p in row_problems
        ):
            # only attempt if the debit/credit numeric checks above passed
            if debit_present or credit_present:
                amount = (debit or Decimal("0")) - (credit or Decimal("0"))
                amount = amount.quantize(Decimal("0.01"))

        # --- required OUTPUT fields: JournalRef, Date, AccountCode, Amount ---
        journal_ref = entry_no
        date_str = posting_date.strftime("%Y-%m-%d") if posting_date else None

        if is_blank(journal_ref):
            row_problems.append("JournalRef (Entry No) is empty")
        if date_str is None:
            row_problems.append("Date could not be derived (see Posting Date issue above)")
        if is_blank(account_code):
            row_problems.append("AccountCode (Account Code) is empty")
        if amount is None:
            row_problems.append("Amount could not be derived (see Debit/Credit issue above)")

        if row_problems:
            flagged.append((i, entry_no, "; ".join(row_problems)))
            continue

        out_rows.append(
            [
                str(journal_ref).strip(),
                date_str,
                str(account_code).strip(),
                "" if is_blank(description) else str(description).strip(),
                f"{amount:.2f}",
                "" if is_blank(cost_centre) else str(cost_centre).strip(),
                SOURCE_CONSTANT,
            ]
        )
        total_amount += amount

    # --- write output CSV ---
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(OUTPUT_HEADER)
        writer.writerows(out_rows)

    # --- write exceptions log (only if there's something to report) ---
    exceptions_path = str(output_path) + ".exceptions.log"
    if flagged:
        with open(exceptions_path, "w", encoding="utf-8") as f:
            f.write(f"Exceptions for conversion of '{source_path}' -> '{output_path}'\n")
            f.write(f"Generated: {datetime.now().isoformat(timespec='seconds')}\n\n")
            for row_num, entry_no, reason in flagged:
                f.write(f"Source row {row_num} (Entry No={entry_no!r}): {reason}\n")

    return {
        "rows_in": len(data_rows),
        "rows_out": len(out_rows),
        "total_amount": total_amount,
        "flagged": flagged,
        "exceptions_path": exceptions_path if flagged else None,
    }


def main():
    if len(sys.argv) != 3:
        print(
            "Usage: python convert_gl_to_journal_import.py <source.xlsx> <output.csv>",
            file=sys.stderr,
        )
        sys.exit(2)

    source_path, output_path = sys.argv[1], sys.argv[2]

    try:
        result = convert(source_path, output_path)
    except SchemaError as e:
        print("SCHEMA/SENSE-CHECK FAILURE -- conversion STOPPED, nothing written.")
        print(str(e))
        sys.exit(1)

    print(f"Source:  {source_path}")
    print(f"Output:  {output_path}")
    print(f"Rows in (data rows in source):  {result['rows_in']}")
    print(f"Rows out (written to CSV):      {result['rows_out']}")
    print(f"Sum of Amount column:           {result['total_amount']:.2f}")
    if result["flagged"]:
        print(f"Rows flagged/excluded:           {len(result['flagged'])}")
        print(f"  See: {result['exceptions_path']}")
        for row_num, entry_no, reason in result["flagged"]:
            print(f"  - row {row_num} (Entry No={entry_no!r}): {reason}")
    else:
        print("Rows flagged/excluded:           0 (no errors)")


if __name__ == "__main__":
    main()
