# Security Policy

**Phronesis Applied — Data Toolkit**

This toolkit is local-first: the compute engines run on the user's machine and do not
upload files, call home, or send telemetry. Please read [`DATA-HANDLING.md`](DATA-HANDLING.md)
for the standing PII / confidential-data rule.

## Supported versions

| Version | Supported |
|---|---|
| Latest `main` / tagged release (currently 0.4.x) | Yes |
| Older tagged releases | Best-effort — please upgrade |

## Reporting a vulnerability

**Please do not open a public GitHub issue for security reports.**

Email **[hello@phronesis-applied.com](mailto:hello@phronesis-applied.com)** with:

- a short description of the issue and its impact
- steps to reproduce (or a proof-of-concept)
- affected version / commit if known
- whether you are okay being credited

We aim to acknowledge within a few business days and to keep you updated until the fix
ships or we explain why we are not treating it as a vulnerability.

## What this project considers in scope

- Bugs in the **local Python engines** that could cause wrong money maths, silent data loss,
  or unsafe defaults (e.g. inventing figures, force-fitting reconciliations)
- Failures of the **PII / confidential-data posture** in shipped code or hooks (egress
  tokenisation guidance, accidental logging of secrets in toolkit code)
- Supply-chain issues in this repository (malicious content, compromised release artefacts)

## Out of scope

- The **Claude / Anthropic host** (Claude Code, Cowork, Claude.ai) — model behaviour,
  prompt injection against the host, and cloud processing of prompts are governed by
  Anthropic's own security and data policies. Report host issues to Anthropic.
- Vulnerabilities that require the user to deliberately disable local safeguards or paste
  secrets into a chat
- Third-party optional dependencies (`PyMuPDF`, `pdfplumber`, etc.) — report upstream;
  we will bump or document once a fix is available
- Social-engineering / phishing that does not involve this codebase

## Data handling summary

- Engines read local files the user points them at and write outputs back to local folders
- No network calls in the core path; dashboards are self-contained HTML (no CDN)
- Shared drives are reached as **synced local paths**, not cloud connectors
- Skills produce **drafts for a qualified person** — never post to ledgers or auto-send

If you believe a shipped code path violates that summary, treat it as in-scope and email us.
