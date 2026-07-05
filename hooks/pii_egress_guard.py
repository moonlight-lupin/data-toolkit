#!/usr/bin/env python
"""Data-handling reminder — a PreToolUse hook on external tools (WebFetch / WebSearch /
any MCP connector). It operationalises the toolkit's #1 rule: keep sensitive or confidential
business RELATIONSHIPS off external services ("search the name, not the relationship").

Deliberately CONSERVATIVE so it doesn't nag during ordinary public research: it stays silent
unless the outbound payload contains a clear relationship leak (e.g. "our LP", "we're
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

# CLEAR relationship leaks → confirm (low false-positive: these reveal a deal/client tie)
STRONG = [
    r"\bour\s+(lp|lps|investor|investors|client|clients|deal|seller|counterparty|target|tenant)\b",
    r"\bwe(?:'re|\s+are|\s+have|\s+will|\s+ll)?\s+(?:investing|acquiring|buying|selling|"
    r"divesting|funding|onboarding|considering)\b",
    r"\b(?:our|the)\s+(?:fund|deal|spv)\s+(?:is\s+)?(?:investing|acquiring|buying)\b",
    r"\b[stfg]\d{7}[a-z]\b",                         # NRIC/FIN-like
    r"\b(?:\d{8,9}[a-z]|\d{4}\d{5}[a-z]|[a-z]\d{2}[a-z]{2}\d{4}[a-z])\b",  # UEN-like
    r"\b\d{3,4}-\d{4,6}-\d{3,4}\b",                 # bank account-like
    r"\b(?:counterparty|vendor|tenant|investor|payee|beneficiary)\b.{0,80}"
    r"\b(?:amount|balance|commitment|invoice|payment|schedule)\b.{0,80}"
    r"\b\d{1,3}(?:,\d{3})+(?:\.\d{2})?\b",          # financial schedule row-like
]
# Sensitive holding data → a soft reminder (more ambiguous, so don't confirm)
HOLDING = [r"\b\d{1,3}\s?%\s?(?:stake|holding|interest|ownership)\b"]


def _hit(pats):
    return any(re.search(p, text) for p in pats)


if _hit(STRONG):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "ask",
        "permissionDecisionReason": (
            "Data-handling: this external call looks like it may reveal a sensitive "
            "deal/client RELATIONSHIP. Search the NAME, not the relationship — tokenise or "
            "omit sensitive PII first (see DATA-HANDLING.md). Proceed?")}}))
    sys.exit(0)

if _hit(HOLDING):
    print(json.dumps({"systemMessage": (
        "Data-handling reminder: this external call may carry sensitive data (a holding %). Send "
        "only public, non-sensitive content — de-identify business/deal PII first (DATA-HANDLING.md).")}))
    sys.exit(0)

sys.exit(0)
