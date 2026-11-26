# Sign-off — Job-Search Agent 3

## Checked
- **Whole-word and case-insensitive matching** (no substring collisions such as `"ai"` in `"maintenance"` or `"email"`, `"r"` in `"engineer"`): verified by unit tests in `tests/` (`pytest -q`, 97 passed).
- **Topic point cap and per-rule deduplication** (repeated keywords in a long posting do not inflate score past the cap): verified by unit tests in `tests/` and deterministic score recomputation in `score_report.py`.
- **Exclusion rule precedence (`X1`–`X5`) and missing-field abstention (`CANNOT_TELL`)**: verified by unit tests in `tests/` and audited against Set A (`39` rows) and held-out Set B (`30` rows).
- **Filter precision and false-negative rate on frozen job snapshots**: verified on Set A (`35/35` rejects agreed; `0.000` sample error rate, 95% Wilson upper bound `0.114`) and Set B (`30/30` agreement across baseline and single-variable ablations).
- **Read-only MCP tool server boundary and client handshake**: verified by unit tests (`pytest -q`, 97 passed), end-to-end execution via `mcp_client.py` (5/5 requests answered), and live session transcript `transcripts/mcp_20261126T011605838379Z.jsonl`.
- **Reference `mcp-server-fetch` SSRF, proxy, and side-effect boundaries** (`modelcontextprotocol/servers` commit `c799c8552b0f27b7a33a7b9233773da144dddcf5`): verified by static source inspection of `server.py`, `pinning.py`, `allowlist.py`, `transport.py`, and `readability_js.py` in `evaluations/EVAL_OTHER_SERVER.md`.

## How
- **By hand:**
  - Authored `FILTER.md` (persona, `R1`–`R5`, `T1`–`T5`, `X1`–`X5`, threshold `5`, and §2 evidence/abstention rules) before running any agent code.
  - Blind-labeled 39 postings in Set A (`labels/set_A_labels.csv`) and 30 held-out postings in Set B (`labels/set_B_labels.csv`).
  - Labeled shortlist claims (`s` / `c` / `i`) in `shortlist/claims.csv` and wrote interpretations in `AUDIT.md`, `SCORE_REPORT.md`, `shortlist/SHORTLIST.md`, `evaluations/EVAL_OWN_SERVER.md`, and `evaluations/EVAL_OTHER_SERVER.md`.
- **By a test I wrote before reading Claude's code:**
  - Defined the pre-code failure cases in `FILTER.md` §4 (substring matching, unbounded keyword frequency bias, unanchored `"pipeline"` / `"forecasting"` / `"associate"` false friends, and silent rejection on missing fields) and enforced them in the test suite (`97 passed`).
- **By recomputation:**
  - Re-ran `run_filter.py` across `v1` (`4` kept), `v2` (`3` kept), and `v3` (`0` kept), `audit.py`, `compare_versions.py`, and `score_report.py` from scratch, confirming byte-identical outputs against committed CSVs and reports.
- **With Claude's help:**
  - Implemented `src/` filtering/scoring modules, `audit.py`, `score_report.py`, `mcp_client.py`, the local MCP server, and the `pytest` suite (`97` tests).
  - Generated structured draft tables for Set A audit (`AUDIT.md`), `SCORE_REPORT_DRAFT.md`, and the static code-reading draft in `evaluations/EVAL_OTHER_SERVER.md`, which I reviewed and signed off with my own interpretations and trust decisions.

## Not checked
1. **Live network scraping or unseen job boards:** Only the frozen 3-board snapshot (`1,167` postings across `cloudflare`, `datadog`, and `palantir` from 2026-11-10) was evaluated; behavior on Workday, Ashby, or live Greenhouse/Lever schema changes was not tested.
2. **External third-party runtime behavior of `mcp-server-fetch`:** `modelcontextprotocol/servers` (`src/fetch`) was audited by source inspection only—its own test suite was not executed, and external library behavior (`httpx` redirect/proxy handling, `readabilipy`'s `ExtractArticle.js` under Node.js) was not verified by execution.
3. **Recall on rare true positives in Set B (`n = 30`):** Because positive entry-level US data/AI postings make up less than 0.4% of the 1,167-posting corpus, the 30-row unweighted random sample in Set B contained `0` positive (`y`) postings and therefore bounds false positives rather than measuring positive recall.

## Not claiming
- **Not claiming model training or weight updates:** Any improvement across sessions came solely from editing `FILTER.md`, adjusting the keep threshold setting, or refining `prompts/justify_claims.md`—no model weights were fine-tuned.
- **Not claiming automated job-application readiness:** This system filters, scores, and verifies quoted evidence from local JSON snapshots; it does not submit applications, authenticate to external portals, or replace human review of role fit.
- **Not claiming general security certification for third-party MCP servers:** My trust decisions in `evaluations/` apply only to the exact inspected local server and pinned commit (`c799c8552b0f27b7a33a7b9233773da144dddcf5`) under the stated CLI/environment restrictions.

## Signed or withheld
Meena Periasamy, 2026-11-25 — **signed** because all deterministic filter rules, version diffs, and held-out Set B ablations are reproducible (`97` passing tests, byte-identical recomputation), every numeric parameter's origin is documented in `SCORE_REPORT.md`, and both the custom MCP tool server and the reference `fetch` server have explicit, source-checked trust boundaries.

## Driver's seat

| Part | What Claude should do | What I should do | Why that part stays mine | Evidence |
|---|---|---|---|---|
| Filter and audit | Implement deterministic rule matching, scoring, and statistical audit scripts (`audit.py`, `score_report.py`) and surface false-friend candidates | Define the persona, author `FILTER.md` rules/thresholds before coding, blind-label Set A and Set B, and decide which rule changes to accept | Only I can define what counts as a valid target role for my career goals and judge whether a rule change fixes a real error vs. overfitting noise | `FILTER.md`, `labels/set_A_labels.csv`, `labels/set_B_labels.csv`, `SCORE_REPORT.md` |
| Shortlist | Extract candidate postings and retrieve verbatim supporting/contradicting sentences from posting descriptions | Verify every claim against the quoted text (`s`/`c`/`i`), write the abstention rule, and identify entailment counterexamples | Keyword retrieval cannot distinguish preferred vs. required skills or team context from role duties; accountability for factual claims stays with me | `prompts/justify_claims.md`, `shortlist/claims.csv`, `shortlist/SHORTLIST.md` |
| Tool server | Scaffold the MCP server/client code, write unit tests, and map line-by-line code paths in server source files | Enforce read-only tool scope, verify tests and transcripts, and write the final trust decisions and operational guardrails | Granting an agent network or filesystem capabilities carries real security risk; only the human operator can accept or restrict that trust boundary | `transcripts/mcp_20261126T011605838379Z.jsonl`, `evaluations/EVAL_OWN_SERVER.md`, `evaluations/EVAL_OTHER_SERVER.md` |
| **Whether a posting is worth my time** | Surface candidates and quote evidence | Judge relevance and label every claim | Only I know what my time is worth; a word match is not a judgment | `labels/`, `shortlist/claims.csv` |