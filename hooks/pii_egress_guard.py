#!/usr/bin/env python
"""Data-handling reminder — a PreToolUse hook on external tools (WebFetch / WebSearch /
any MCP connector). It operationalises the toolkit's #1 rule: keep personal and confidential
data off external services ("search the public fact, not the private record").

Deliberately CONSERVATIVE so it doesn't nag during ordinary public research: it stays silent
unless the outbound payload contains a clear leak of personal data (e.g. an email + name, a
government/account ID) or a confidential business relationship (e.g. "our client", "we're
acquiring X"), in which case it asks the user to confirm. It NEVER hard-blocks — it's a
reminder/confirm, guidance-not-gate, not a DLP control. Tune the patterns below to taste. Reads the tool call on
stdin; emits a decision on stdout; exit 0 always.

Docs: stdin = {tool_name, tool_input, ...}; for a confirm we return
hookSpecificOutput.permissionDecision = "ask"; for a soft reminder we return systemMessage.
"""
import json
import re
import sys

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

ti = data.get("tool_input") or {}
parts = []


def _collect(v):
    if isinstance(v, str):
        parts.append(v)
    elif isinstance(v, dict):
        for x in v.values():
            _collect(x)
    elif isinstance(v, list):
        for x in v:
            _collect(x)


_collect(ti)
text = " ".join(parts).lower()

# CLEAR leaks of personal or confidential data → confirm (low false-positive)
STRONG = [
    r"\bour\s+(customer|customers|client|clients|supplier|suppliers|vendor|"
    r"employee|employees|patient|patients|deal|seller|counterparty|target)\b",
    r"\bwe(?:'re|\s+are|\s+have|\s+will|\s+ll)?\s+(?:investing|acquiring|buying|selling|"
    r"divesting|funding|onboarding|considering)\b",
    r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b",                 # email address (personal identifier)
    r"\b[stfg]\d{7}[a-z]\b",                         # NRIC/FIN-like national ID
    r"\b(?:\d{8,9}[a-z]|\d{4}\d{5}[a-z]|[a-z]\d{2}[a-z]{2}\d{4}[a-z])\b",  # company/UEN-like
    r"\b(?:\+?\d[\d\s-]{7,}\d)\b",                   # phone / long numeric ID
    r"\b\d{3,4}-\d{4,6}-\d{3,4}\b",                 # bank account / card-like
    r"\b(?:customer|counterparty|vendor|payee|beneficiary|account)\b.{0,80}"
    r"\b(?:amount|balance|invoice|payment|salary|schedule)\b.{0,80}"
    r"\b\d{1,3}(?:,\d{3})+(?:\.\d{2})?\b",          # financial schedule row-like
]
# Sensitive holding/ownership data → a soft reminder (more ambiguous, so don't confirm)
HOLDING = [r"\b\d{1,3}\s?%\s?(?:stake|holding|interest|ownership)\b"]


def _hit(pats):
    return any(re.search(p, text) for p in pats)


if _hit(STRONG):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "ask",
        "permissionDecisionReason": (
            "Data-handling: this external call looks like it may carry personal or "
            "confidential data (a name/ID/contact detail or a private business record). "
            "Send the public fact, not the private record — tokenise or omit the sensitive "
            "data first (see DATA-HANDLING.md). Proceed?")}}))
    sys.exit(0)

if _hit(HOLDING):
    print(json.dumps({"systemMessage": (
        "Data-handling reminder: this external call may carry sensitive data (a holding %). Send "
        "only public, non-sensitive content — de-identify personal/confidential data first (DATA-HANDLING.md).")}))
    sys.exit(0)

sys.exit(0)
