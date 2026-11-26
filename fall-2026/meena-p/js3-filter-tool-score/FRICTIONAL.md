# Frictional Log — Job-Search Agent 3

Written by Meena Periasamy (2026-11-25).  
Scope: Build, audit, MCP tool server, and sign-off for `js3-filter-tool-score` (commits `7b96757` through `b8b1be1`).

## 1. `FILTER.md` v1 baseline vs. build defaults (`7b96757` -> `4923b21`)
Started `FILTER.md` (`7b96757`) by raising the keep threshold from the build guide's `>= 4` to `>= 5` (`src/config.py`) so a posting could not pass on topic keywords alone without a title match. Later (`4923b21`), I expanded the baseline rules to separate core role titles (`R1`–`R4`) from seniority qualifiers (`R5`) and added explicit location (`X3`), non-target domain (`X4`), and experience/PhD (`X5`) exclusions—though the file header stayed labeled `v1` while the v2/v3 scoring logic diverged in `src/config.py` and `src/filter.py`.

## 2. First look at Set A labels vs. `FILTER.md` v1 (`AUDIT.md`, `labels/set_A_labels.csv`)
On the 39 Set A postings, the filter agreed with my blind labels on all `35/35` rejects (`30/30` random rejects and `5/5` close calls), but `3` of the `4` `KEPT` postings (`75%`) were false positives (`GTM Strategy/Operations Associate`, an international/experienced `Data Scientist`, and an experienced `Data Analyst`). High recall on obvious rejects hid severe precision problems at the top of the funnel because non-US offices and experienced roles without `"Senior"` in the title cleared the `>= 5` score bar.

## 3. False friends and the `v2` `"associate"` cut (`src/filter.py`, `SCORE_REPORT.md`)
Auditing the 69 candidate rule matches in Set A exposed recurring lexical false friends: `"pipeline"` firing on B2B sales pipelines (`Account Executive`, `BDR`), `"forecasting"` firing on sales quota and corporate FP&A (`Strategic Finance`), and `"associate"` in `R5` admitting `GTM Strategy/Operations Associate` (`greenhouse/8171303`, score `6`). For `v2` (`ROLE_RULES_V2` in `src/filter.py`), I cut `"associate"` from `R5`—which removed `greenhouse/8171303` across the full 1,167-posting corpus—though I never synced that `v2` diff back into `FILTER.md` itself.

## 4. Claude Code implementation drift between `FILTER.md` and `src/` (`4923b21`, `src/location.py`)
When Claude Code translated `FILTER.md` into `src/config.py` and `src/location.py`, it introduced a 16-city `US_CITIES` allowlist for `X3` as a judgment call that was not specified in `FILTER.md`, and left `v3` (`run_filter.py --version v3`) keeping `0` of `1,167` postings because `X3` and `X5` were too strict on the frozen snapshot. Checking `SCORE_REPORT.md` caught where numbers were hand-set by me versus inferred by Claude Code during implementation.

## 5. `make_sheets.py` refusal and `pytest` environment mismatch (`a59923c`, `README.md`)
Re-running `make_sheets.py` exited with status `1` by design because `labels/set_A_labels.csv` and `labels/set_B_labels.csv` already contained my verdicts, preventing accidental overwrites. Separately, running `pytest -q` in a fresh venv failed because dependencies were not installed, while running `.venv/bin/python -m pytest -q` passed `97` tests—deviating from the older test count documented in `README.md`.

## 6. MCP server connection, transcript capture, and static audit gaps (`3bc6d20`, `transcripts/mcp_20261126T011605838379Z.jsonl`)
The local read-only MCP server (`mcp_client.py`) connected cleanly over stdio and answered all 5 test requests in `transcripts/mcp_20261126T011605838379Z.jsonl`. By contrast, auditing the reference `mcp-server-fetch` (`modelcontextprotocol/servers` commit `c799c8552b0f27b7a33a7b9233773da144dddcf5` in `evaluations/EVAL_OTHER_SERVER.md`) revealed subtle gaps between its `readOnlyHint: true` annotation and actual runtime behavior—including an unguarded `npm install` on first HTML fetch when `node` is on `PATH`, proxy environment variables bypassing `pinning.py` private-IP checks, and `robots.txt` being skipped on the user prompt path.

## 7. What remains unresolved (`SCORE_REPORT.md`, `SHORTLIST.md`)
Because true entry-level US data/AI roles make up less than `0.4%` of the 1,167-posting snapshot (`3` kept in `v2`), the 30-row random sample in Set B drew `0` positive (`y`) postings (`30/30` agreement, `0` kept), meaning Set B bounds false keeps (`0/30`) but cannot measure positive recall. Additionally, `FILTER.md` header versioning (`v1` vs. `v2`/`v3` in `src/`) and stratified positive-recall sampling remain open for a future iteration.