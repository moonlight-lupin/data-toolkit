# Data Toolkit — Data handling & PII policy

**Standing policy for every skill in this plugin.** Default to the cautious, auditable
approach when handling sensitive or confidential business/financial data. This is the
single source of the data-handling rule; every skill's "Data handling" section points here.

> Referenced by every skill's `## Data handling` section. Keep it as the one place the
> rule lives.

## What is gated (and what is not)

Two classes are gated — **deal-specific** and **counterparty/individual-specific**
information:

- **Deal-specific** — a counterparty, seller, vendor, JV partner or asset identified
  **in connection with an actual deal or transaction**, and deal terms tied to a named
  party. The trigger is the **linkage to a live deal**, not the name on its own.
- **Holder-specific** — named individuals or entities together with their **holdings,
  commitments or percentages** (e.g. a party named as holding **>25%** of an entity).

**Not gated by itself: a bare counterparty name with no deal attached.** *Drafting or
signing an agreement does not imply a deal exists* — a party name on its own is not
deal-specific PII, and need not be tokenised. It becomes gated only when it is tied to
a **specific deal or asset** (then the linkage is what reveals the deal). When a name
and a live deal travel together, tokenise the pairing.

Plus the baseline: **tenant and valuation data**, and personal data of identifiable
individuals — handle with the same care.

## The rule: tokenise on egress

**Before deal-specific or holder-specific PII crosses to any external or third-party tool,
replace it with a stable token and keep the mapping local.**

- "Egress to external/third-party" = web searches; external APIs; online file converters;
  any AI service that is **not** this account; any upload to a service not deliberately
  chosen for that purpose.
- **Tokens** are stable and meaningless: `Counterparty A`, `Seller-1`, `Holder-01`,
  `UBO-01`. Keep a **local token map** (a file in the working folder on your synced or
  shared file store — **never uploaded**) so outputs can be re-identified locally after
  the external step.
- **Re-identify locally**, in this account / on the machine, once the external step
  returns.

## Where real values ARE allowed (the deliberate-purpose carve-out)

Tokenisation guards *egress*. Real names are fine when the data stays in a controlled
place or goes to a recipient entitled to it:

- Local processing on **your synced or shared file store**, MS Office (Word/Excel COM) on
  the user's machine, and this account's own reasoning.
- Inside a **deliverable that legitimately requires the name and goes to the entitled
  party** — e.g. the counterparty's own agreement, or a letter (with its required schedule)
  addressed to the relying party. That is the "deliberately chosen tool for that purpose"
  carve-out.

**When in doubt, tokenise and ask.**

## How it lands per skill

| Skill | Application |
|---|---|
| `data-tidy` | Processes data **locally** — gated PII never leaves the machine. Tokenise only if a downstream step (a different skill) would push a value to an external tool. |
| `data-extract` | Same: extraction runs **locally**; the clean `.xlsx` + audit report stay on the local/synced store. |
| `data-reconcile` | Same: matching/triage runs **locally** and produces a working paper for review — no egress, nothing posted. |
| `data-visualise` | Embeds data directly into a self-contained `.html` and never calls out (no CDN/remote images). Keep the file on the local/synced store; if it carries deal-specific / holder-specific data, treat it as gated — only share with entitled recipients. A firm-level board with no such data is not gated. |

> **General rule for any handoff:** if a value would cross to an external/third-party tool
> (web search, external API, online converter, a cloud artifact runtime), de-identify it
> first per the gating rules above.

## Environment facts that shape this

- **No Microsoft 365 connector is assumed.** The toolkit does not reach a shared file
  store via an M365 MCP.
- **Shared stores are reached as synced local files.** A SharePoint / OneDrive / Drive
  library that syncs into the file system is reached as an ordinary **local path** — not a
  connector. This is *why* the toolkit is built around local file I/O, and it keeps PII on
  the local/synced store rather than pushing it through a cloud connector. The local token
  map lives here too.
