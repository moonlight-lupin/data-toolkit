# Data Toolkit — Data handling & PII policy

**Standing policy for every skill in this plugin.** Default to the cautious, auditable
approach when handling personal, sensitive or confidential business/financial data. This is
the single source of the data-handling rule; every skill's "Data handling" section points here.

> Referenced by every skill's `## Data handling` section. Keep it as the one place the
> rule lives.

## What is gated (and what is not)

Two classes are gated — **personal data** and **confidential business/financial data**:

- **Personal data (PII)** — information that identifies a living individual: a name
  **together with** contact details, an address, a date of birth, a government / tax / national
  ID, an account, card or policy number, salary, or health data. A bare name in a public
  context is not automatically sensitive; it becomes PII when tied to identifying or private
  attributes (the linkage is what identifies the person).
- **Confidential business/financial data** — non-public information a business would not want
  disclosed: customer / supplier lists, pricing, revenue, margins and unpublished financials,
  contract terms, and anything marked confidential or clearly proprietary.

**Not gated by itself: information that is already public, or aggregated/anonymised so no
individual or confidential figure can be recovered.** A published company name, a public
address, or a headline statistic with no personal or proprietary detail need not be tokenised.
Data becomes gated when a personal identifier or a confidential figure travels with it — then
tokenise the pairing.

Treat anything a client, customer or counterparty gave you in confidence as sensitive by
default. When in doubt, gate it.

## The rule: tokenise on egress

**Before personal or confidential data crosses to any external or third-party tool, replace it
with a stable token and keep the mapping local.**

- "Egress to external/third-party" = web searches; external APIs; online file converters;
  any AI service that is **not** this account; any upload to a service not deliberately
  chosen for that purpose.
- **Tokens** are stable and meaningless: `Person A`, `Customer-1`, `Account-01`, `ID-01`.
  Keep a **local token map** (a file in the working folder on your synced or shared file
  store — **never uploaded**) so outputs can be re-identified locally after the external step.
- **Re-identify locally**, in this account / on the machine, once the external step returns.

## Where real values ARE allowed (the deliberate-purpose carve-out)

Tokenisation guards *egress*. Real names and figures are fine when the data stays in a
controlled place or goes to a recipient entitled to it:

- Local processing on **your synced or shared file store**, MS Office (Word/Excel COM) on
  the user's machine, and this account's own reasoning.
- Inside a **deliverable that legitimately requires the data and goes to the entitled
  party** — e.g. a customer's own statement, or a letter (with its required schedule)
  addressed to the person it concerns. That is the "deliberately chosen tool for that purpose"
  carve-out.

**When in doubt, tokenise and ask.**

## How it lands per skill

| Skill | Application |
|---|---|
| `data-tidy` | Processes data **locally** — gated data never leaves the machine. Tokenise only if a downstream step (a different skill) would push a value to an external tool. |
| `data-extract` | Same: extraction runs **locally**; the clean `.xlsx` + audit report stay on the local/synced store. |
| `data-reconcile` | Same: matching/triage runs **locally** and produces a working paper for review — no egress, nothing posted. |
| `data-analyse` | Same: metrics and the insight brief are computed **locally**; brief + metrics workbook stay on the local/synced store. A brief that names individuals or quotes confidential figures is gated on any egress. |
| `data-visualise` | Embeds data directly into a self-contained `.html` and never calls out (no CDN/remote images). Keep the file on the local/synced store; if it carries personal or confidential business/financial data, treat it as gated — only share with entitled recipients. A board built purely from non-sensitive, aggregated numbers is not gated. |

> **General rule for any handoff:** if a value would cross to an external/third-party tool
> (web search, external API, online converter, a cloud artifact runtime), de-identify it
> first per the gating rules above.

## Environment facts that shape this

- **No Microsoft 365 connector is assumed.** The toolkit does not reach a shared file
  store via an M365 MCP.
- **Shared stores are reached as synced local files.** A SharePoint / OneDrive / Drive
  library that syncs into the file system is reached as an ordinary **local path** — not a
  connector. This is *why* the toolkit is built around local file I/O, and it keeps sensitive
  data on the local/synced store rather than pushing it through a cloud connector. The local
  token map lives here too.
