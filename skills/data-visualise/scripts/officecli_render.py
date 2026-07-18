"""officecli_render.py — OPTIONAL chart rendering via the OfficeCLI binary.

Narrow-scope adapter for the one thing `openpyxl` cannot do: turn the charts inside an
`.xlsx` we just wrote into **images**. Everything here is opt-in and degrades to "not
available" — the toolkit never requires OfficeCLI, and chart generation itself stays on
openpyxl (the existing hard dependency).

    from officecli_render import available, render_chart_pngs
    if available():
        pngs = render_chart_pngs("charts.xlsx", out_dir)   # one PNG per chart

OfficeCLI (https://github.com/iOfficeAI/OfficeCLI, Apache-2.0) is a **third-party**,
self-contained binary — not a Python package. Install it separately (`brew install
officecli`, `scoop install officecli`, `npm i -g @officecli/officecli`, or a release
binary) and make sure `officecli` is on PATH. Its project documentation states it runs
fully locally with no network access or API keys; that is the vendor's claim, which this
toolkit relays rather than certifies — see `../../../DATA-HANDLING.md`.

Design notes:
- **This is the toolkit's only subprocess.** Calls are made with an argument list (never
  ``shell=True``), never interpolate caller data into a shell string, are time-boxed, and
  a non-zero exit or a timeout degrades to "no image" rather than raising.
- **Rendering only.** We do not let OfficeCLI author or mutate a workbook — openpyxl writes
  the file, OfficeCLI only reads it to produce a picture. That keeps the deterministic
  engine as the single source of the numbers.
- **PNG only for .xlsx.** OfficeCLI's `svg` view mode is pptx-only (verified against
  v1.0.131), so an Excel chart renders to PNG.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

BINARY = "officecli"
DEFAULT_TIMEOUT = 60          # a single chart render measured ~1.8s; this is a safety rail
DEFAULT_WIDTH = 1600
DEFAULT_HEIGHT = 1200


def binary_path() -> str | None:
    """Absolute path to the officecli binary, or None when it is not installed."""
    return shutil.which(BINARY)


def available() -> bool:
    return binary_path() is not None


def _run(args: list[str], *, timeout: int = DEFAULT_TIMEOUT) -> tuple[int, str, str]:
    """Run officecli with an argument list. Returns (returncode, stdout, stderr).

    Never raises for the ordinary failure modes (missing binary, non-zero exit, timeout) —
    rendering is a bonus, so a failure must not take the run down with it.
    """
    exe = binary_path()
    if not exe:
        return 127, "", f"{BINARY} not found on PATH"
    try:
        proc = subprocess.run(                      # noqa: S603 - list args, shell=False
            [exe, *args],
            shell=False,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return proc.returncode, proc.stdout or "", proc.stderr or ""
    except subprocess.TimeoutExpired:
        return 124, "", f"{BINARY} timed out after {timeout}s"
    except OSError as exc:                           # binary vanished / not executable
        return 126, "", f"{BINARY} could not be executed: {exc}"


def version() -> str | None:
    """OfficeCLI version string, or None. Worth recording in a run report: the project
    releases very frequently, so 'which build produced this image' is a real question."""
    code, out, _err = _run(["--version"], timeout=15)
    if code != 0:
        return None
    return (out.strip().splitlines() or [""])[0].strip() or None


def chart_paths(xlsx_path: str | Path, *, timeout: int = DEFAULT_TIMEOUT) -> list[str]:
    """Data-paths of every chart in the workbook, e.g. ``/By region/chart[1]``.

    These are what `--range` crops to; a cell range does **not** work, because a chart is a
    floating object rather than cell content.
    """
    code, out, _err = _run(["query", str(xlsx_path), "chart", "--json"], timeout=timeout)
    if code != 0 or not out.strip():
        return []
    try:
        payload = json.loads(out)
    except json.JSONDecodeError:
        return []
    results = (payload.get("data") or {}).get("results") or []
    return [r["path"] for r in results if isinstance(r, dict) and r.get("path")]


def _safe_stem(path: str) -> str:
    """A filesystem-safe stem from a chart data-path (``/By region/chart[1]``)."""
    return re.sub(r"[^\w.-]+", "_", path).strip("_") or "chart"


def release(xlsx_path: str | Path, *, timeout: int = 30) -> bool:
    """Close OfficeCLI's *resident* process for this file and release the OS file lock.

    Reading a document starts a resident that keeps it in memory — and on Windows that holds
    an open handle, so the caller cannot then move, delete or re-write the workbook (and the
    user cannot open it in Excel) until it is closed. Every render path below calls this in a
    ``finally``; it is idempotent and a no-op when no resident is active.
    """
    if not available():
        return False
    code, _out, _err = _run(["close", str(xlsx_path)], timeout=timeout)
    return code == 0


def render_chart_pngs(
    xlsx_path: str | Path,
    out_dir: str | Path,
    *,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    timeout: int = DEFAULT_TIMEOUT,
    prefix: str = "",
) -> list[Path]:
    """Render one PNG per chart in the workbook, cropped to each chart's bounding box.

    Returns the PNGs actually written (empty list when OfficeCLI is unavailable or nothing
    rendered). Never raises for an unavailable/failing binary.
    """
    if not available():
        return []
    out_dir = Path(out_dir)
    written: list[Path] = []
    try:
        for i, chart_path in enumerate(chart_paths(xlsx_path, timeout=timeout), start=1):
            target = out_dir / f"{prefix}{i:02d}-{_safe_stem(chart_path)}.png"
            target.parent.mkdir(parents=True, exist_ok=True)
            code, _out, _err = _run(
                ["view", str(xlsx_path), "screenshot", "-o", str(target),
                 "--range", chart_path,
                 "--screenshot-width", str(int(width)),
                 "--screenshot-height", str(int(height))],
                timeout=timeout,
            )
            if code == 0 and target.is_file() and target.stat().st_size > 0:
                written.append(target)
    finally:
        release(xlsx_path)      # never leave the workbook locked by a resident
    return written


def render_sheet_png(
    xlsx_path: str | Path,
    out_png: str | Path,
    *,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    timeout: int = DEFAULT_TIMEOUT,
) -> Path | None:
    """Render the first sheet (chart included) to one PNG. None if unavailable/failed."""
    if not available():
        return None
    out_png = Path(out_png)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    try:
        code, _out, _err = _run(
            ["view", str(xlsx_path), "screenshot", "-o", str(out_png),
             "--screenshot-width", str(int(width)),
             "--screenshot-height", str(int(height))],
            timeout=timeout,
        )
    finally:
        release(xlsx_path)      # never leave the workbook locked by a resident
    return out_png if code == 0 and out_png.is_file() and out_png.stat().st_size > 0 else None


def status() -> dict[str, Any]:
    """Probe summary for envcheck / run reports."""
    path = binary_path()
    return {"available": path is not None, "path": path, "version": version() if path else None}


if __name__ == "__main__":
    import sys

    st = status()
    print(f"officecli available : {st['available']}")
    print(f"officecli path      : {st['path'] or '(not on PATH)'}")
    print(f"officecli version   : {st['version'] or '-'}")
    if len(sys.argv) > 1:
        src = sys.argv[1]
        print(f"charts in {src}: {chart_paths(src)}")
        out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path.cwd() / "officecli-render"
        print("rendered:", [str(p) for p in render_chart_pngs(src, out)])
