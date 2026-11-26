# Job-Search Agent 3 — filter, audit, shortlist, MCP tool

Job-Search Agent 3 (JS3) scores job postings against a hand-written filter (`FILTER.md`). It then
audits that filter against blind hand labels, builds a shortlist of claims that must be backed by
evidence, and exposes the scoring as one read-only Model Context Protocol (MCP) tool.

- **No real résumé is used anywhere in this project.**
- **The persona is fictional:** Jordan Lee, an entry-level or new-grad Data Engineer, Data
  Scientist, BI Analyst or AI/ML Engineer looking for individual-contributor roles in the US or
  remote.
- **The MCP tool server is read-only.** It sends no network requests. The only file it writes is
  its own transcript in `transcripts/`.

## Where it started

JS3 started from my Job-Search Agent 2 (`../js2-loop-tools-diff/`). JS2's saved raw board
responses from its run `20261110T203921572430Z` (2026-11-10 20:39:21 UTC) were copied byte for
byte into `data/raw/`:
- `cloudflare` and `datadog` on Greenhouse
- `palantir` on Lever

`data/SOURCES_OF_DATA.md` records each source path, its size and sha256, and the request URLs.
JS3 makes no network requests and never modified the JS2 folder.

## Language and toolchain

- Python 3.12. The project venv was built from Python 3.12.15.
- Standard library only for all JS3 code.
- `pytest==9.2.0` for the tests.
- `requests==2.34.2` is pinned in `requirements.txt` but **no JS3 code imports it**. It was kept
  for an optional fresh fetch, which wasn't needed because the JS2 bodies already contained full
  descriptions.

## Commands from a fresh clone

Run these from this folder (`fall-2026/meena-p/js3-filter-tool-score/`):

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt   # needs network (PyPI); the only online step

.venv/bin/python run_filter.py                  # v1 -> output/filter_results.csv
.venv/bin/python run_filter.py --version v2     # v2 -> output/filter_results_v2.csv
.venv/bin/python run_filter.py --version v3     # v3 -> output/filter_results_v3.csv
.venv/bin/python make_sheets.py                 # blind labeling sets A and B (see note)
.venv/bin/python audit.py                       # set A audit -> audit/AUDIT_REPORT_DRAFT.md
.venv/bin/python compare_versions.py            # v1 vs v2 on set B -> audit/RULE_CHANGE_v2.md
.venv/bin/python score_report.py                # number origins + experiments -> SCORE_REPORT_DRAFT.md
.venv/bin/python mcp_client.py                  # MCP demo: starts mcp_server.py, prints replies
.venv/bin/python -m pytest -q                   # all tests, offline
```

Notes:
- **`make_sheets.py` exits with code 1 in a clone that already has labels.** It refuses to
  overwrite a `labels/*_labels.csv` file that contains any verdict. That refusal is the expected
  result here, because the committed labels are mine.
- **Several commands overwrite committed files with regenerated copies:**
  - `run_filter.py`: the CSVs in `output/`
  - `audit.py`: `audit/AUDIT_REPORT_DRAFT.md`
  - `compare_versions.py`: `audit/RULE_CHANGE_v2.md`
  - `score_report.py`: `SCORE_REPORT_DRAFT.md`

  The human-written files (`audit/AUDIT_REPORT.md`, `SCORE_REPORT.md`) are never touched by these
  scripts.
- **`mcp_client.py` writes a new file in `transcripts/` on every run.**

Labeling is interactive and needs a terminal:

```bash
.venv/bin/python label.py labels/set_A_labels.csv           # y / n / ? / f (full text) / q
.venv/bin/python label.py labels/set_B_labels.csv
.venv/bin/python label_claims.py shortlist/claims.csv       # s / c / i / f / q
```

Both tools skip rows that already have a verdict and save after every answer.

## Registering the MCP server with Claude Code

```bash
claude mcp add js3-filter -- "$PWD/.venv/bin/python" "$PWD/mcp_server.py"
# add  -s project  to write it to a shared .mcp.json instead of local scope
```

The server offers one tool, `score_posting {"posting_id": string}`.
- **What it returns:** the decision, score, `rules_fired` and `close_call` from rule set v3
  (`src/filter_v3.py`), which implements `FILTER.md` as committed in `4923b21`.
- **When it refuses:** if FILTER.md's sha256 no longer matches the version v3 was built from, it
  won't score.
- **Evaluation:** `evaluations/EVAL_OWN_SERVER.md` lists what it does and doesn't enforce.

## What ran, and when

Only runs whose output is saved in this folder are listed. Dates are 2026-11-25 (US Eastern)
unless marked UTC.

| What ran | Saved output | Committed in |
|---|---|---|
| JS2 board fetch (2026-11-10 20:39:21 UTC) | `data/raw/*.body`, `data/SOURCES_OF_DATA.md` | `4923b21` |
| JS2 recon (read-only) | `notes/recon_2026-11-25.md` | `2325a40` |
| Filter v1 on all 1,167 postings: 4 kept | `output/filter_results.csv` | `4923b21` |
| `make_sheets.py`, seed 20261125: set A has 39 rows (only 4 kept postings existed), set B has 30 | `labels/set_*_key.csv`, `labels/set_*_labels.csv` | `31f260c` (with my verdicts) |
| `audit.py` on set A | `audit/AUDIT_REPORT_DRAFT.md` | `4923b21` |
| Filter v2 ("associate" removed from R5): 3 kept | `output/filter_results_v2.csv` | `4923b21` |
| `compare_versions.py` (v1 vs v2 on set B) | `audit/RULE_CHANGE_v2.md` | `4923b21` |
| Claim drafting for the 3 v2-kept postings | `shortlist/claims.csv`, `notes/shortlist_draft_2026-11-25.md` | `a59923c` |
| A pytest run that collected no tests | `notes/tests_after_build.txt` ("no tests ran in 0.00s") | `2325a40` |
| Filter v3 (committed FILTER.md): 0 kept, 3 close calls | `output/filter_results_v3.csv` | `7610235` |
| `mcp_client.py` demo, 2026-11-26 01:15:10 UTC: initialize, tools/list, three tools/call | `transcripts/mcp_20261126T011510667170Z.jsonl` | `7610235` |
| Claude Code 2.1.332 connected to the server, 2026-11-26 01:16:03 and 01:16:05 UTC: initialize and tools/list only, **no tool call** | `transcripts/mcp_20261126T011603062737Z.jsonl`, `…011605838379Z.jsonl` | `7610235`, `3bc6d20` |
| `score_report.py` (threshold 5→4; filter v2→v1; set B only) | `SCORE_REPORT_DRAFT.md` | `f833e98` |

## Deliverables

Status as of 2026-11-25, commit `6be02b2`:

| Deliverable | What it is | Status |
|---|---|---|
| `FILTER.md` | the filter contract, written by me before any code | committed (`6be02b2`). The Version line says v3 (sections 1–3 are the v3 rules) and names the version each entry point uses. The change log has rows for v1, v2, v3 and the v2 + threshold 4 experiment. **The Decision cells for v2, v3 and the experiment say "pending my decision"** |
| `audit/` | `AUDIT_REPORT_DRAFT.md` (computed), `AUDIT_REPORT.md` (my interpretation), `RULE_CHANGE_v2.md` (computed) | committed |
| `shortlist/` | `claims.csv` (9 claims with my labels), `SHORTLIST.md` | `claims.csv` labeled. **`SHORTLIST.md` still contains template placeholders** |
| `transcripts/` | MCP JSONL transcripts, both directions | 7 committed: the `mcp_client.py` demo (`…011510…`); two Claude Code sessions with no tool call (`…011603…`, `…011605…`); four `mcp_client.py` verification runs after the FILTER.md change-log edit (`…015428…`, `…015704…`, `…015813…`, `…015903…`, committed in `6be02b2`) |
| `evaluations/` | `EVAL_OWN_SERVER.md`, `EVAL_OTHER_SERVER.md` (MCP fetch reference server) | both committed. My trust decision is written in `EVAL_OTHER_SERVER.md`; **`EVAL_OWN_SERVER.md` still says "To be written by me"** |
| `SCORE_REPORT.md` | number origins, set B experiments, my interpretation | committed. The empty draft "Interpretation" heading is still above mine |
| `SIGNOFF.md` | sign-off | committed (`6b9af0f`) |
| `FRICTIONAL.md` | Frictional reflection | committed (`6b9af0f`) |
| `SOURCES.md` | provenance of data, references, and who wrote what | committed (`6b9af0f`) |

## Code map

| Path | Role |
|---|---|
| `src/postings.py` | loads `data/raw/`; strips Greenhouse HTML; deduplicates by provider and id |
| `src/filter.py` | rule sets v1 and v2 (original FILTER.md contract) |
| `src/filter_v3.py`, `src/location.py` | rule set v3 (FILTER.md as committed in `4923b21`) and US-location test |
| `src/config.py` | every number, each commented with its origin |
| `run_filter.py`, `make_sheets.py`, `audit.py`, `compare_versions.py`, `score_report.py` | the steps listed above |
| `label.py`, `label_claims.py` | blind labeling tools |
| `mcp_server.py`, `mcp_client.py` | MCP server (JSON-RPC 2.0 over stdio, no SDK) and demo client |
| `tests/` | `test_filter.py` (v1/v2), `test_filter_v3.py`, `test_mcp.py` |
| `prompts/justify_claims.md` | the prompt used to draft shortlist claims |
