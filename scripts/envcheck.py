"""Data Toolkit — environment pre-screen.

Probes the current machine for what the toolkit's skills need (OS, Python version,
the input-adapter libraries, and local Tesseract for scanned-PDF OCR), then prints a
per-skill readiness line. Run before using a skill if the environment is uncertain:

    python scripts/envcheck.py

The toolkit's engine runs on your machine and makes no network calls (the AI agent driving it
does send whatever it reads to your AI provider — see DATA-HANDLING.md). Most jobs
(xlsx / csv / paste / digital PDF) need only openpyxl; heavier inputs (PDF, .docx,
.msg) and OCR add optional dependencies that degrade cleanly when absent.

NOTE: this can't detect session-level capabilities — whether a browser is available
to preview/print a visualisation depends on the environment, not this probe.
See COMPATIBILITY.md.
"""

import importlib.util
import platform
import shutil
import sys

# The default Windows console is cp1252 and can't encode the glyphs below
# (✗, ·), which would crash this prober in the toolkit's own primary mode
# (Claude Code local on Windows). Switch stdout to UTF-8 where supported.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

OK, DEGRADED, BLOCKED, CHECK = "OK", "DEGRADED", "BLOCKED", "CHECK"


def has(mod):
    return importlib.util.find_spec(mod) is not None


def main():
    tesseract = shutil.which("tesseract")          # local OCR engine for scanned-PDF input

    print("=== Data Toolkit environment pre-screen ===")
    print(f"OS                : {platform.system()} {platform.release()}")
    print(f"Python            : {platform.python_version()}")
    print(f"Tesseract (OCR)   : {tesseract or 'not found (scanned-PDF OCR unavailable)'}")
    # Shared-engine input adapters. openpyxl is the only hard dependency; the rest are
    # optional input formats imported lazily and degraded with a clear message.
    libs = ["openpyxl", "fitz", "pdfplumber", "docx", "pptx", "extract_msg", "pyarrow", "pandas"]
    labels = {"fitz": "fitz (PyMuPDF)", "docx": "docx (python-docx)",
              "pptx": "pptx (python-pptx)",
              "pdfplumber": "pdfplumber (PDF tables, optional)",
              "pyarrow": "pyarrow (large-file Parquet, optional)",
              "pandas": "pandas (large-file / read_large, optional)"}
    print("Python libs       : " + ", ".join(
        f"{labels.get(m, m)}{'' if has(m) else '✗'}" for m in libs))
    print()

    def libs_ok(*mods):
        miss = [m for m in mods if not has(m)]
        return (BLOCKED, "missing: " + ", ".join(miss)) if miss else (OK, "")

    # (skill, "built-for mode", status, note)
    rows = []

    def add(skill, mode, status, note):
        rows.append((skill, mode, status, note))

    # data-tidy — openpyxl core; PDF/docx/msg optional; OCR needs local Tesseract
    s, n = libs_ok("openpyxl")
    if s == OK:
        opt = [lib for lib, mod in [("PyMuPDF/PDF", "fitz"), ("pdfplumber/messy-PDF-tables", "pdfplumber"),
                                    (".docx", "docx"), (".pptx", "pptx"),
                                    (".msg", "extract_msg"),
                                    ("pyarrow/large-files", "pyarrow"),
                                    ("pandas/large-files", "pandas")] if not has(mod)]
        if not tesseract:
            opt.append("Tesseract/OCR-scans")
        n = "xlsx/csv/paste ready; optional inputs missing: " + ", ".join(opt) if opt \
            else "all input adapters available (incl. OCR + large-file)"
    add("data-tidy", "any (portable); OCR needs local Tesseract", s, n)

    # data-extract — PyMuPDF for PDF docs (main input) + openpyxl out; OCR via local Tesseract
    s, n = libs_ok("fitz", "openpyxl")
    if s == OK:
        extra = [] if has("pdfplumber") else ["pdfplumber/messy-tables"]
        if not has("docx"):
            extra.append(".docx")
        if not has("pptx"):
            extra.append(".pptx")
        if not has("extract_msg"):
            extra.append(".msg")
        if not tesseract:
            extra.append("OCR-scans")
        if not has("PIL"):
            extra.append("Pillow/image-compress")
        n = "PDF/form extraction ready" + (f"; optional missing: {', '.join(extra)}" if extra else " (incl. OCR)")
        n += "; image/chart extract needs vision API key (VISION_API_KEY)"
    add("data-extract", "any (portable); PDF + OCR (local Tesseract); vision API optional", s, n)

    # data-reconcile — openpyxl core (xlsx working paper); CSV/PDF/docx/msg via shared engine
    s, n = libs_ok("openpyxl")
    if s == OK:
        opt = [lib for lib, mod in [("PyMuPDF/PDF", "fitz"), ("pdfplumber/messy-PDF-tables", "pdfplumber"),
                                    (".docx", "docx"), (".pptx", "pptx"),
                                    (".msg", "extract_msg")] if not has(mod)]
        n = "xlsx/csv ready; optional inputs missing: " + ", ".join(opt) if opt \
            else "all input adapters available"
    add("data-reconcile", "any (portable); no network", s, n)

    # data-analyse — openpyxl core (xlsx in / metrics workbook out); other inputs optional
    s, n = libs_ok("openpyxl")
    if s == OK:
        opt = [lib for lib, mod in [("PyMuPDF/PDF", "fitz"), ("pdfplumber/messy-PDF-tables", "pdfplumber"),
                                    (".docx", "docx"), (".pptx", "pptx"),
                                    (".msg", "extract_msg"),
                                    ("pyarrow/large-files", "pyarrow"),
                                    ("pandas/large-files", "pandas")] if not has(mod)]
        n = "xlsx/csv ready; optional inputs missing: " + ", ".join(opt) if opt \
            else "all input adapters available (incl. large-file)"
    add("data-analyse", "any (portable); no network", s, n)

    # data-visualise — pure stdlib HTML/SVG; openpyxl only to read an .xlsx source
    n = ("ready (stdlib HTML/SVG); CJK/i18n labels use browser font fallback"
         + ("" if has("openpyxl") else "; add openpyxl to read .xlsx sources")
         + "; preview needs a browser only")
    add("data-visualise", "any (portable)", OK, n)

    w = max(len(r[0]) for r in rows)
    print(f"{'SKILL'.ljust(w)}  STATUS     NOTE")
    for sk, mode, st, note in rows:
        print(f"{sk.ljust(w)}  {st.ljust(9)}  {note}")
    print("\nLegend: OK ready · DEGRADED works with lower fidelity · BLOCKED missing a "
          "hard need · CHECK depends on session mode (see COMPATIBILITY.md).")


if __name__ == "__main__":
    main()
