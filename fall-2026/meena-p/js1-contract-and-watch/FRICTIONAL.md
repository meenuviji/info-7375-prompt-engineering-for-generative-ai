# FRICTIONAL — Job-Search Agent 1

## Timeline (UTC)

| UTC | Event | Ref | Detail | Source | Notes |
|---|---|---|---|---|---|
| 2026-10-31T17:36:19Z | commit | `56f30ea` | Contract and labeling rule, written before code | git log |  |
| 2026-10-31T17:37:25Z | commit | `1ce1af0` | Fill in CONTRACT.md before any code | git log |  |
| 2026-10-31T18:18:38Z | commit | `94f5ede` | Resolve contract placeholders: fields, rule keywords, wrong version 3, failure sentence | git log |  |
| 2026-10-31T18:21:34Z | commit | `d138c84` | Watch: allow-listed fetch, state by id, seeded two-run evidence | git log |  |
| 2026-10-31T18:25:54Z | commit | `9c8c20a` | Fill board token and persona city in contract | git log |  |
| 2026-10-31T18:32:56Z | commit | `0bb2599` | Test for wrong version 1: misaligned labels | git log |  |
| 2026-10-31T18:35:54Z | commit | `c1506ed` | README: drop stale open-contract-items section | git log |  |
| 2026-10-31T18:39:48Z..19:52:16Z | validator rejections | `evidence/claude_calls.jsonl` | 0 of 70 Claude judge calls rejected by `agent/validator.py`; 0 retries; 0 INVALID | evidence/claude_calls.jsonl |  |
| 2026-10-31T18:40:37Z | commit | `bbd5e0b` | Two judges: rule RECORD and Claude JUDGMENT with validator | git log |  |
| 2026-10-31T18:40:37Z..18:45:52Z | test failure | between `bbd5e0b` and `7cc4199` | 1 failed, 79 passed: `test_system_prompt_loaded_from_file_verbatim` (StopIteration: test fake had 1 response for 2 calls) | pytest output in Claude Code session (not saved to a file) |  |
| 2026-10-31T18:45:52Z | commit | `7cc4199` | Move system prompt into prompts/ for versioning | git log |  |
| 2026-10-31T18:58:02Z | commit | `f097cf0` | Labeling sheet, labels blank, stratified selection | git log |  |
| 2026-10-31T19:11:03Z | commit | `c3732b9` | Hand labels by Meena per LABELING.md | git log |  |
| 2026-10-31T19:15:52Z | commit | `f4fec9d` | Sampling report and v1 baseline on dev | git log |  |
| 2026-10-31T19:25:11Z | commit | `8cbaad6` | Fix judge_v2 prompt and rationale before any held-out run | git log |  |
| 2026-10-31T19:28:01Z | commit | `ecb3ddc` | v2: one change to Clause 2; held-out evaluated last | git log |  |
| 2026-10-31T19:37:30Z | commit | `8694582` | Fix stale wording in heldout_eval.py | git log |  |
| 2026-10-31T19:47:06Z | commit | `7af69f2` | Action-surface comparison draft | git log |  |
| 2026-10-31T19:47:06Z | validator result | `7af69f2`, `reports/ACTION-SURFACE.md` | chat-paste justification (Meena's claude.ai run) through `agent/validate.py`: `['no resume field cited']` | check run by Claude Code; recorded in ACTION-SURFACE.md |  |
| 2026-10-31T19:50:10Z | commit | `6632159` | Failing test: made-up indexed path passes justification validation | git log |  |
| 2026-10-31T19:50:10Z | test failure | `6632159` | 4 failed, 82 passed: `test_text_validator_rejects_made_up_indexed_path` [3 params], `test_claude_validator_rejects_made_up_indexed_path_in_text` | failing-test commit; pytest output in session |  |
| 2026-10-31T19:50:28Z | commit | `baffe7f` | Fix: made-up indexed path passes justification validation | git log |  |
| 2026-10-31T19:51:01Z | commit | `96abd18` | Failing test: state written before judging completes | git log |  |
| 2026-10-31T19:51:01Z | test failure | `96abd18` | 1 failed, 87 passed: `test_state_not_updated_when_judging_fails` | failing-test commit; pytest output in session |  |
| 2026-10-31T19:51:08Z | commit | `c809e8e` | Fix: state written before judging completes | git log |  |
| 2026-10-31T19:51:24Z | commit | `bdd8f18` | Failing test: fetch follows redirects off the allow-list | git log |  |
| 2026-10-31T19:51:24Z | test failure | `bdd8f18` | 3 failed, 89 passed: `test_fetch_refuses_redirect_off_allow_list` [301, 302, 307] | failing-test commit; pytest output in session |  |
| 2026-10-31T19:51:24Z..19:51:47Z | test failure | `6314e2a` (unpushed; amended into `9b6aa2a`) | 1 failed, 91 passed: `test_fetch_saves_raw_bytes_unmodified` (AttributeError: fake response had no `status_code`); commit was made with this failure, then amended | pytest output in session |  |
| 2026-10-31T19:51:47Z | commit | `9b6aa2a` | Fix: fetch follows redirects off the allow-list | git log |  |
| 2026-10-31T19:52:54Z | commit | `0b6adb1` | Post-fix SEEDED re-run; mark three gaps fixed in ACTION-SURFACE | git log |  |
| 2026-10-31T20:09:06Z | commit | `ad6cb7b` | Least autonomy section rewritten by Meena | git log |  |
