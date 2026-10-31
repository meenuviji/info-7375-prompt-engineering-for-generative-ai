# FRICTIONAL — Job-Search Agent 1

## Timeline (UTC)

| UTC | Event | Ref | Detail | Source | Notes |
|---|---|---|---|---|---|
| 2026-10-31T17:36:19Z | commit | `56f30ea` | Contract and labeling rule, written before code | git log | I committed CONTRACT.md at 0 bytes; ls -la showed it, and I filled it in the next commit. |
| 2026-10-31T17:37:25Z | commit | `1ce1af0` | Fill in CONTRACT.md before any code | git log |  |
| 2026-10-31T18:18:38Z | commit | `94f5ede` | Resolve contract placeholders: fields, rule keywords, wrong version 3, failure sentence | git log | Claude Code refused to build until I filled the contract placeholders and asked me which persona fields to use; I chose personal.location and skills. |
| 2026-10-31T18:21:34Z | commit | `d138c84` | Watch: allow-listed fetch, state by id, seeded two-run evidence | git log |  |
| 2026-10-31T18:25:54Z | commit | `9c8c20a` | Fill board token and persona city in contract | git log | My grep for "<" missed the HERE placeholders, so the board token and city were filled after the first code commit; no rule changed. |
| 2026-10-31T18:32:56Z | commit | `0bb2599` | Test for wrong version 1: misaligned labels | git log | I checked the tests by name and thought wrong version 1 had none; it did, so this added a second test for it. |
| 2026-10-31T18:35:54Z | commit | `c1506ed` | README: drop stale open-contract-items section | git log |  |
| 2026-10-31T18:39:48Z..19:52:16Z | validator rejections | `evidence/claude_calls.jsonl` | 0 of 70 Claude judge calls rejected by `agent/validator.py`; 0 retries; 0 INVALID | evidence/claude_calls.jsonl |  |
| 2026-10-31T18:40:37Z | commit | `bbd5e0b` | Two judges: rule RECORD and Claude JUDGMENT with validator | git log |  |
| 2026-10-31T18:40:37Z..18:45:52Z | test failure | between `bbd5e0b` and `7cc4199` | 1 failed, 79 passed: `test_system_prompt_loaded_from_file_verbatim` (StopIteration: test fake had 1 response for 2 calls) | pytest output in Claude Code session (not saved to a file) |  |
| 2026-10-31T18:45:52Z | commit | `7cc4199` | Move system prompt into prompts/ for versioning | git log | Claude Code had put a system prompt in code; I made it move into prompts/ so the prompts I submit are the prompts I ran. |
| 2026-10-31T18:58:02Z | commit | `f097cf0` | Labeling sheet, labels blank, stratified selection | git log |  |
| 2026-10-31T19:11:03Z | commit | `c3732b9` | Hand labels by Meena per LABELING.md | git log | All 20 of my labels came out not_relevant because the cloudflare board has nothing for a Boston early-career persona, so the experiment cannot separate v1, v2 and a constant judge. |
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
| 2026-10-31T20:14:46Z | commit | `7cf1eb1` | Final assembly: README, SOURCES, FRICTIONAL timeline | git log |  |
| 2026-10-31T20:22:16Z | commit | `007c19b` | README: identify assignment and student | git log |  |
| 2026-10-31T20:22:35Z | commit | `70aab50` | SOURCES: note on chat-surface evidence | git log |  |
| 2026-10-31T20:51:14Z | commit | `03d92dd` | Meena: correct contract provenance line, held-out outcome statement, chat header | git log | First occurrence of older content overwriting newer edits in CONTRACT.md and EXPERIMENT.md; I suspected an external editor conflict, restored files via git (4e3936d), and kept monitoring. |
| 2026-10-31T20:52:51Z | commit | `85c213d` | Failing test (audit row 2): rule judge cites posting.location.name when the posting has none | git log |  |
| 2026-10-31T20:52:51Z | test failure | `85c213d` | 3 failed, 92 passed: `test_rule_without_location_cites_only_existing_fields` [3 params] | failing-test commit; pytest output in session |  |
| 2026-10-31T20:53:08Z | commit | `f0ae1d2` | Fix (audit row 2): rule judge cites posting.location.name only when it exists | git log |  |
| 2026-10-31T20:53:23Z | commit | `27e68c3` | Fix (audit row 8): replace non-555 test phone with (555) 432-0163 | git log |  |
| 2026-10-31T20:53:40Z | commit | `3df468e` | Fix (audit row 5): preserve SEEDED state after each run (reproduced from saved files) | git log |  |
| 2026-10-31T20:53:48Z | commit | `5003516` | Fix (audit row 12): resolve contradiction about re-running the agent in ACTION-SURFACE.md | git log |  |
| 2026-10-31T20:54:10Z | commit | `3060d6b` | Fix (audit row 15): correct chat-evidence note and attribution in SOURCES.md | git log |  |
| 2026-10-31T20:54:17Z | commit | `d36ea95` | Fix (audit row 19): note in README that Canvas folder name overrides assignment-XX | git log |  |
| 2026-10-31T20:54:33Z | commit | `6a9e851` | Fix (audit row 16): add missing commits to FRICTIONAL timeline (Notes left empty) | git log |  |
| 2026-10-31T20:56:38Z | commit | `9f1f4a9` | Fix (audit row 14): correct stale report-regeneration claim in README | git log |  |
| 2026-10-31T21:02:05Z | commit | `4e3936d` | Restore CONTRACT.md and EXPERIMENT.md overwritten by stale editor copy in 03d92dd; correct contract provenance line | git log |  |
| 2026-10-31T21:10:30Z | commit | `d9101c9` | Held-out outcome statement (Meena) | git log | Second occurrence of the same overwrite failure; from the repeated pattern I concluded (but did not prove) that a stale TextEdit window's autosave was reverting working files, so I abandoned TextEdit completely and adopted verbatim insertion via Claude Code. |
| 2026-10-31T21:19:43Z | commit | `01d4eee` | Restore EXPERIMENT.md overwritten in d9101c9; keep Meena's 3 outcome lines | git log |  |
| 2026-10-31T21:31:44Z | commit | `6548eef` | Chat header: time and model (Meena, inserted verbatim) | git log |  |
| 2026-10-31T21:32:20Z | commit | `c2ec7ad` | SAMPLING conclusion (Meena, inserted verbatim) | git log |  |
| 2026-10-31T21:34:51Z | commit | `6616c45` | Driver's seat (Meena, inserted verbatim) | git log |  |
| 2026-10-31T21:36:49Z | commit | `332ad15` | FRICTIONAL note: editor overwrites (Meena, inserted verbatim) | git log |  |
| 2026-10-31T21:37:41Z | commit | `0a633fa` | SOURCES: editor note and wording help (Meena, inserted verbatim) | git log |  |
| 2026-10-31T22:05:56Z | commit | `f3de644` | Sign-off (Meena, inserted verbatim) | git log |  |
| 2026-10-31T22:07:56Z | commit | `10ae2ae` | Driver's seat: accurate evidence for course repo row (Meena) | git log |  |
| 2026-10-31T22:15:11Z | commit | `3bc9d75` | ACTION-SURFACE: quote current chat header (factual fix) | git log |  |
| 2026-10-31T22:19:04Z | commit | `6de8b65` | FRICTIONAL notes (Meena, inserted verbatim) | git log |  |
| 2026-10-31T22:19:37Z | commit | `e1b5fc2` | FRICTIONAL: timeline row for 6de8b65 | git log |  |
| 2026-10-31T22:19:56Z | commit | `08b2e7e` | FRICTIONAL: timeline row for e1b5fc2 | git log |  |
| 2026-10-31T22:20:34Z | commit | `cd1dc40` | FRICTIONAL: timeline row for 08b2e7e | git log |  |
| 2026-10-31T22:21:08Z | commit | `a900232` | FRICTIONAL: timeline row for cd1dc40 | git log |  |
| 2026-10-31T22:22:26Z | commit | `6613d51` | FRICTIONAL: timeline row for a900232 | git log |  |
| 2026-10-31T22:23:46Z | commit | `52cd963` | FRICTIONAL: timeline row for 6613d51 | git log |  |
| 2026-10-31T22:25:13Z | commit | `2b4bd13` | FRICTIONAL: timeline row for 52cd963 | git log |  |
