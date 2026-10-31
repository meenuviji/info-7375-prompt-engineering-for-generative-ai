INFO7375 — Job-Search Agent 1: The Contract and the Watch. Student: Meena Periasamy. Submitted 2026-10-31.

# the_contract_watch — Job-Search Agent 1 (contract and watch)

Watches one public Greenhouse job board (`cloudflare`) for new postings, identified by `id`, and judges each new posting for one fictional persona (Priya Nair) two ways: a deterministic rule (RECORD) and a Claude judgment (JUDGMENT, model output, not fact). Everything is implemented against [CONTRACT.md](CONTRACT.md). Hand labels follow [LABELING.md](LABELING.md). Reports are in [reports/](reports/), evidence in [evidence/](evidence/), and authorship in [SOURCES.md](SOURCES.md).

**Submission location:** the course repo copy lives at `fall-2026/meena-p/js1-contract-and-watch/`. The Canvas assignment specifies that folder name exactly, and it overrides the `assignment-XX/` convention in the course repo's `ASSESSMENT.md` and `prerequisites/github-submission.md`.

## Language and toolchain
Recorded on 2026-10-31 on the machine that produced the evidence:

| Tool | Version |
|---|---|
| Python | 3.12.15 (venv; system `python3` is 3.9 and is not used) |
| requests | 2.34.2 |
| pytest | 9.2.0 |
| anthropic (SDK, used only if `ANTHROPIC_API_KEY` is set) | 2.3.0 |
| Claude Code CLI (`claude -p`, used when no API key is set) | 2.1.316 |
| git | 2.54.0 |
| OS | macOS 27.0.1 |

All Python package versions, including transitive ones, are pinned in `requirements.txt`.

## From a fresh clone
```sh
git clone https://github.com/meenuviji/the_contract_watch.git
cd the_contract_watch
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Claude backend, used for the Claude judge only:
```sh
export JUDGE_MODEL=claude-sonnet-5-5   # optional; this is the default and was used for all evidence
# either set an API key (Anthropic SDK path) ...
export ANTHROPIC_API_KEY=...
# ... or leave it unset and be logged in to the Claude Code CLI (`claude`), which is the path used for all evidence.
```

Tests (no network, no Claude calls; every test's call log is redirected away from `evidence/` by `tests/conftest.py`):
```sh
.venv/bin/python -m pytest -v
```

### Reproduce the SEEDED two-run evidence (from saved files, no live fetch)
Use a scratch state file and runs directory so `state/seen_ids.json` and `evidence/runs/` are not overwritten.
```sh
OUT=/tmp/js1-repro && mkdir -p $OUT
# rebuild the SEEDED earlier snapshot; byte-identical to evidence/raw/SEEDED_earlier.json
.venv/bin/python scripts/make_seeded.py evidence/raw/20261031T182100Z_live.json $OUT/SEEDED_earlier.json
cmp $OUT/SEEDED_earlier.json evidence/raw/SEEDED_earlier.json
# run 1 (baseline) and run 2; --no-judge reproduces the original runs (no Claude calls)
.venv/bin/python -m agent.run --from-file evidence/raw/SEEDED_earlier.json --label SEEDED-earlier \
    --state $OUT/SEEDED_seen_ids.json --runs-dir $OUT --no-judge
.venv/bin/python -m agent.run --from-file evidence/raw/20261031T182100Z_live.json --label live-vs-SEEDED-baseline \
    --state $OUT/SEEDED_seen_ids.json --runs-dir $OUT --no-judge
```
Expected: run 1 reports 459 postings and 0 new; run 2 reports 464 postings and 5 new: 8332361, 8335069, 8335468, 8335469, 8338018. These commands were run on 2026-10-31 and gave exactly that.

**Post-fix variant** (as in `evidence/runs/post-fix/`): the same two commands without `--no-judge`, run into a fresh `--state`/`--runs-dir`. Run 2 then also calls both judges on the 5 new postings (5 Claude calls, appended to `evidence/claude_calls.jsonl`) and writes `<run>_verdicts.json`. State is written only after both judges finish.

Re-judge a saved run without touching state (5 Claude calls):
```sh
.venv/bin/python -m agent.run --rejudge evidence/runs/20261031T182105Z_live-vs-SEEDED-baseline.json
```

A live run (`.venv/bin/python -m agent.run --label live`) fetches the board and updates `state/seen_ids.json`. It was **not** used for the evidence; the board was fetched exactly once, fetch-only (see "What ran").

### Regenerate the labeling sheet and the reports
```sh
# labeling sheet (writes blank my_label/notes): write to a scratch path, not over the hand-labeled file
PYTHONPATH=. .venv/bin/python scripts/make_labeling_sheet.py evidence/raw/20261031T182100Z_live.json /tmp/js1-repro/sheet.csv

# reports from saved evidence (no Claude calls)
PYTHONPATH=. .venv/bin/python scripts/dev_reports.py render     # rewrites reports/SAMPLING.md and the top of reports/EXPERIMENT.md
PYTHONPATH=. .venv/bin/python scripts/heldout_eval.py render    # re-renders the results and Limits block of EXPERIMENT.md
git diff reports/            # see the warning below for what changes
git checkout -- reports/     # restore them
```
**Warning:** `dev_reports.py render` regenerates the two reports from scratch, so it removes hand-written sections (Meena's "The one change I chose and why", and "My conclusion" once written). `heldout_eval.py render` also re-creates the generated results and Limits block, which is not in the current `EXPERIMENT.md`: Meena's commit `03d92dd` removed it, and it is still in `70aab50`. Checked on 2026-10-31 at `6a9e851`: after both renders, `EXPERIMENT.md` changes by 68 lines (Meena's 2 section lines removed, 66 generated lines added), and `SAMPLING.md` is unchanged. `reports/ACTION-SURFACE.md` has no generator.

Re-making the Claude calls behind the reports (`scripts/dev_reports.py run`, `scripts/heldout_eval.py run`, `scripts/surface_file_read.py`) produces new model outputs, which may differ from the saved ones, and appends to the call log.

## Layout
- `agent/fetch.py`: allow-list `ALLOWED_HOSTS = {"boards-api.greenhouse.io"}`, checked before any network call. Redirects are refused. The raw response is saved byte-for-byte to `evidence/raw/<UTC>_<label>.json`.
- `agent/state.py`: `state/seen_ids.json`. New = ids in the response that are not in state. No state file = baseline (0 new).
- `agent/persona.py`: refuses to run unless `personal.location` and `skills` exist, every email ends in `@example.com`, and every phone uses 555. Refusals name fields, never values.
- `agent/rule_judge.py`: CONTRACT.md "The rule", deterministic, `kind="RECORD"`.
- `agent/claude_judge.py`: one fresh, stateless call per posting, `kind="JUDGMENT"`. Prompts: `prompts/system_v1.txt` + `prompts/judge_v1.txt` (or `judge_v2.txt`). Every call is logged to `evidence/claude_calls.jsonl`.
- `agent/validator.py`: strict check of Claude output (JSON shape, exact keys, verdict string, `posting_id`, cited paths, including list indexes). One retry, then `INVALID` with the raw text. Never repairs output.
- `agent/validate.py`: justification citation validator and alignment checker (CONTRACT.md wrong versions 1 and 2).
- `agent/run.py`: CLI (`--label`, `--from-file`, `--rejudge`, `--no-judge`, `--state`, `--runs-dir`).
- `scripts/`: `make_seeded.py`, `make_labeling_sheet.py`, `dev_reports.py`, `heldout_eval.py`, `surface_file_read.py`.
- `resume/persona.json`: fictional persona, copied unmodified from the-reallocation-engine `search/examples/priya-nair/resume.example.json`.
- `labels/postings_20.csv`: 20 postings (10 dev / 10 heldout, seed 7375), hand-labeled by Meena.
- `reports/`: [SAMPLING.md](reports/SAMPLING.md), [EXPERIMENT.md](reports/EXPERIMENT.md), [ACTION-SURFACE.md](reports/ACTION-SURFACE.md).
- [FRICTIONAL.md](FRICTIONAL.md): timeline of commits, test failures and validator results.

## Evidence notes: SEEDED / CONSTRUCTED artifacts
Both two-run pairs (original and post-fix) are **SEEDED**. Both runs happened on 2026-10-31, so the "earlier" snapshot is constructed, not observed. The 5 "new" postings are new only relative to the SEEDED baseline, not new on the board since an earlier real fetch.

| File | Status |
|---|---|
| `evidence/raw/20261031T182100Z_live.json` | **Real** live response from Greenhouse board `cloudflare`, unmodified (464 jobs). The only live fetch. |
| `evidence/raw/SEEDED_earlier.json` | **SEEDED / CONSTRUCTED.** The live response with exactly 5 postings removed: the last 5 by sorted numeric id (8332361, 8335069, 8335468, 8335469, 8338018). The other 459 jobs and `meta` are unchanged (`meta.total` still says 464). Re-serialized with indentation. |
| `evidence/runs/20261031T182105Z_seeded-earlier.json` | Run 1 (baseline) against the **SEEDED** file: 459 postings, 0 new. |
| `evidence/runs/20261031T182105Z_live-vs-SEEDED-baseline.json` | Run 2 against the real live response, diffed against the **SEEDED** baseline state: 5 new, exactly the 5 removed ids. |
| `evidence/runs/20261031T182105Z_live-vs-SEEDED-baseline_verdicts.json` | Rule and Claude verdicts for those 5, from `--rejudge` at 18:39Z. |
| `evidence/runs/post-fix/` | **SEEDED** two-run re-done after the three fixes (commits `baffe7f`, `c809e8e`, `9b6aa2a`), with its own state file `SEEDED_seen_ids.json`: same 5 new ids, judged. |
| `evidence/runs/SEEDED-state-snapshots/` | **SEEDED** two-run reproduced at 20:53:33Z from the saved files (`--no-judge`, no fetch, no Claude calls) to preserve the state after each run, which the original runs overwrote: `SEEDED_state_after_run1_baseline.json` (459 ids, = the ids in `SEEDED_earlier.json`) and `SEEDED_state_after_run2.json` (464 ids, identical to `state/seen_ids.json` and `post-fix/SEEDED_seen_ids.json`). These are reproductions, not the original runs' files. |
| `evidence/runs/20261031T191349Z_sampling_dev.json`, `..._experiment_v1_dev.json`, `20261031T192603Z_v2_eval.json` | Sampling and prompt-experiment results (dev, then held-out). |
| `evidence/claude_calls.jsonl` | Every Claude judge call (70 lines). The first 5 (18:39Z) have no `system_prompt_file`: they ran while the system prompt was still hard-coded with the same text now in `prompts/system_v1.txt`. |
| `evidence/surface_chat_prompt.txt`, `evidence/surface_chat_2026-10-31.txt` | Meena's manual claude.ai run; model and time fields are unfilled placeholders. |
| `evidence/surface_file_*.json`, `evidence/surface_file_prompt.txt` | Read-only `claude -p` run on posting 8335469 (transcript included). |
| `state/seen_ids.json` | State after the original run 2 (464 ids). |

All posting data in `tests/` is CONSTRUCTED; the `*_WRONG` functions there are CONSTRUCTED wrong implementations.

## What ran
Only commands actually run on 2026-10-31, in UTC. Times come from run files, `evidence/claude_calls.jsonl`, transcripts and git. Where none was recorded, the table says so. Ad-hoc inspection one-liners and the many `pytest` runs are not listed individually.

| UTC | Command | Result |
|---|---|---|
| 18:21:00Z | `python -m agent.fetch live` | The only live fetch: `evidence/raw/20261031T182100Z_live.json`, 464 postings |
| 18:21:05Z (file mtime) | `python scripts/make_seeded.py evidence/raw/20261031T182100Z_live.json` | `evidence/raw/SEEDED_earlier.json`, 459 postings (**SEEDED**) |
| 18:21:05Z | `python -m agent.run --from-file evidence/raw/SEEDED_earlier.json --label seeded-earlier` | Baseline, 0 new (**SEEDED**) |
| 18:21:05Z | `python -m agent.run --from-file evidence/raw/20261031T182100Z_live.json --label live-vs-SEEDED-baseline` | 5 new (vs **SEEDED** baseline) |
| not recorded (before 18:39:48Z) | `claude -p ... 'Reply with exactly: {"ok": true}'` | 1 probe call to learn the CLI's JSON output format; not logged to a file |
| 18:39:48Z–18:40:01Z | `python -m agent.run --rejudge evidence/runs/20261031T182105Z_live-vs-SEEDED-baseline.json` | 5 Claude calls, all valid; rule and Claude `not_relevant` for all 5 |
| not recorded (before 18:58:02Z) | `python scripts/make_labeling_sheet.py evidence/raw/20261031T182100Z_live.json` | `labels/postings_20.csv`, blank labels |
| 19:13:49Z (calls 19:13:52Z–19:15:34Z) | `python scripts/dev_reports.py run`, then `render` | 20 sampling calls + 10 v1 dev calls, all valid |
| 19:26:03Z (calls 19:26:06Z–19:27:44Z) | `python scripts/heldout_eval.py run`, then `render` (re-rendered after `8694582`) | 10 v2 dev + 10 v1 held-out + 10 v2 held-out calls, all valid. First held-out call 19:26:41Z, after `8cbaad6` (19:25:11Z) |
| 19:45:46Z | `python scripts/surface_file_read.py` | 1 read-only `claude -p` call on 8335469 (not in `claude_calls.jsonl`; transcript in `evidence/surface_file_output.json`) |
| 19:52:00Z (calls to 19:52:16Z) | the two `agent.run --from-file` commands above, labels `SEEDED-earlier` / `live-vs-SEEDED-baseline`, into `evidence/runs/post-fix/` | Post-fix **SEEDED** two-run: 0 new, then the same 5 new; 5 Claude calls, all valid |

Meena's manual claude.ai chat run on 8335469 is recorded in `evidence/surface_chat_2026-10-31.txt`. Its time field reads `<3.43 pm>` and its model field is an unfilled placeholder.

**The board did not match the persona.** In the live response, 0 of 464 postings have "Boston" in `posting.location.name`, and the contract's rule judges 0 of 464 relevant. Every judge verdict in the evidence (rule, v1, v2) is `not_relevant`, and so is every one of Meena's 20 hand labels.

## Sign-off — Job-Search Agent 1

**Checked:**
- New postings are found by id, not title: `test_new_is_by_id_not_title`, `test_check_catches_new_by_title` (wrong version 3). The live board had two postings with the same title and different ids (8335468, 8335469).
- Justifications cite only fields that exist: `test_validator_catches_bad_citations[*]` (wrong version 2), including the indexed-path case after its fix.
- Verdicts stay paired with their own posting: `test_alignment_catches_off_by_one`, `test_alignment_catches_verdict_paired_with_next_id` (wrong version 1).
- The three gaps Claude Code found (redirects off the allow-list, state written before judging, made-up indexed paths) each have a failing-test commit followed by a fix commit.
- Baseline reports 0 new; the second run reports exactly the 5 ids removed from the SEEDED file, before and after the fixes.
- Full suite: 95 passed, run by me on 2026-10-31.

**How:** Claude Code wrote the code and the tests. I checked each test name against the wrong versions in my contract by hand, read the verdicts and justifications, and ran pytest myself. I wrote the contract before any code, but I did not write tests before reading Claude's code. I hand-labeled all 20 postings using LABELING.md.

**Not checked:**
1. Any posting I labeled relevant. There were none, so false negatives were never tested, and v1, v2 and a constant "not_relevant" judge all scored 10/10.
2. Any board other than cloudflare, or a second calendar day. Both two-run pairs are SEEDED.
3. Case-sensitivity of rule clauses 2 and 3. The contract only says case-insensitive for clause 1, so a lowercase "senior" or "remote" is not caught.
4. Whether `dontAsk` blocks a read outside the temp directory in the file-read surface.
5. Agreement with any second labeler. I am the only labeler.

**Not claiming:** that this agent finds good jobs for this persona; that judge_v2 is better than judge_v1; that the Claude judge is accurate. I only claim that it repeated the same verdict on easy negatives.

**Signed:** Meena Periasamy, 2026-10-31, subject to the Not checked list above.
## Driver's seat
| Part of the task | What Claude did | What I did | Why it stays mine | Evidence |
|---|---|---|---|---|
| Contract and rule | Drafted a template (claude.ai); Claude Code refused to build until placeholders were filled | Chose the rule, fields, wrong versions and failure sentence; filled and committed them before code | The rule decides what "relevant" means for me; a TA must be able to apply it by hand | 56f30ea, 1ce1af0, 94f5ede (all before d138c84) |
| Code and tests | Wrote the agent, both judges, the validator and the tests | Checked test names against my wrong versions; ran pytest myself; made it move a hidden system prompt into prompts/ | I answer for what the tests prove, not Claude | 7cc4199; my pytest runs |
| Hand labels | None; it was told not to suggest labels | Labeled all 20 postings against LABELING.md | If Claude labels, the experiment grades itself | c3732b9 |
| The one prompt change | Ran v1/v2 on dev, then held-out | Chose the Clause 2 change after the dev results and wrote its rationale | Choosing what to change is the experiment's decision | EXPERIMENT.md section; 8cbaad6 before the first held-out call |
| Security gaps | Found the redirect, state-timing and indexed-path gaps while comparing surfaces | Decided to fix them test-first rather than only document them | Deciding what ships is my call | bdd8f18/9b6aa2a, 96abd18/c809e8e, 6632159/baffe7f |
| Least autonomy | Drafted a version marked DRAFT | Rewrote it, citing the chat surface's justification that cited no résumé field | The autonomy choice is the judgment the assignment grades | ad6cb7b |
| Course repo folder | Proposed renaming it to assignment-01 | Cancelled the rename; kept js1-contract-and-watch/ as Canvas specifies | Submission format is my responsibility | course repo info-7375-prompt-engineering-for-generative-ai: b275073 (folder js1-contract-and-watch); rename cancelled before commit; this repo: d36ea95 |
