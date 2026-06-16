#!/usr/bin/env python
"""SKILL.md hygiene — a PostToolUse hook on Write/Edit. After a SKILL.md is written, it
checks the recurring breakages and warns (non-blocking) so they're fixed before the skill is
relied on: (1) CRLF line endings (the skills viewer needs LF), (2) `---` must be line 1, and
(3) frontmatter should be name + description only (extra keys break the viewer's parse).

It WARNS, it doesn't modify the file or block — the model/maintainer fixes it. Only acts on
files named SKILL.md; silent otherwise. Reads the tool call on stdin; exit 0 always.
"""
import json
import re
import sys

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

fp = (data.get("tool_input") or {}).get("file_path", "")
if not fp.replace("\\", "/").endswith("/SKILL.md") and not fp.endswith("SKILL.md"):
    sys.exit(0)

try:
    raw = open(fp, "rb").read()
except Exception:
    sys.exit(0)

issues = []
if b"\r\n" in raw:
    issues.append("CRLF line endings — must be LF (CRLF breaks the skills-viewer frontmatter parse)")

txt = raw.decode("utf-8", errors="ignore")
if not txt.startswith("---\n"):
    issues.append("first line must be '---' (YAML frontmatter opener)")
elif txt.count("---") >= 2:
    fm = txt.split("---", 2)[1]
    keys = re.findall(r"^([A-Za-z_]+):", fm, re.M)
    extra = [k for k in keys if k not in ("name", "description")]
    if extra:
        issues.append("frontmatter should be name + description only; extra key(s): " + ", ".join(extra))

if issues:
    msg = ("SKILL.md hygiene — " + fp + ": " + "; ".join(issues) +
           ". Fix before relying on it (normalise to LF; keep frontmatter = name/description only).")
    print(json.dumps({"systemMessage": msg, "additionalContext": msg,
                      "hookSpecificOutput": {"hookEventName": "PostToolUse"}}))
sys.exit(0)
