# Job-Search Agent 2 (JS2): loop, tools and diff

JS2 polls public job boards in a bounded loop. It fetches each board, validates the response
by its structure, compares the posting ids with the previous run (added / removed /
unchanged), keeps one state file per board, and writes an append-only trace of every
attempt. The contract is [GATE.md](GATE.md); where its sections disagree, the later
section wins (section 9 and its subsections override sections 1–8).

## What this started from

JS2 started from my Job-Search Agent 1 code (`js1-contract-and-watch`, from my
`the_contract_watch` repository). **Only `agent/fetch.py` and `agent/state.py` carried over**,
as the starting points for [src/fetch.py](src/fetch.py) and [src/state.py](src/state.py). Both
were changed for JS2; their docstrings list what was kept and what changed. JS1's Claude
judge, rule judge, persona, `--rejudge`, scripts, labels, evidence and state files were not
copied.

## Language and toolchain

- **Language:** Python 3.12. The system `python3` on the development machine is 3.9 and cannot run this code.
- **Dependencies:** [requirements.txt](requirements.txt), installed into a local `.venv`:
  `requests` 2.34.2 (used only by the live transport, plus its pinned dependencies) and `pytest` 9.2.0.
- **Offline by default:** every test runs offline through a scripted fake transport. Only
  `python -m src.loop` touches the network.

## Commands from a fresh clone

```bash
git clone https://github.com/meenuviji/info-7375-prompt-engineering-for-generative-ai.git
cd info-7375-prompt-engineering-for-generative-ai/fall-2026/meena-p/js2-loop-tools-diff

# 1. Create the virtual environment with Python 3.12 and install
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 2. Run the tests (offline)
.venv/bin/python -m pytest -q

# 3. Run the independent checker on the SEEDED demo traces (offline)
.venv/bin/python -I check_independent.py tests/fixtures/SEEDED_truncated_cloudflare.json output/demo/finished_wrong_trace.jsonl
.venv/bin/python -I check_independent.py tests/fixtures/SEEDED_truncated_cloudflare.json output/demo/gate_catches_trace.jsonl

# 4. Run the agent against the live network
.venv/bin/python -m src.loop --config config/boards.json
.venv/bin/python -m src.loop --config config/boards_with_failures.json
```

Notes on these commands:
- **Checker arguments:** `check_independent.py` needs both arguments (the fixture, then a
  trace). Run without them, it stops with an `IndexError`; see
  `output/demo/independent_check_run_by_me.txt`.
- **Checker exit status:** **1** on the first trace (verdict `WRONG`, the expected result for
  the seeded demo) and **0** on the second (verdict `CAUGHT`).
- **`-I`:** runs Python in isolated mode, so the checker cannot import anything from this
  project, even by accident.
- **Before step 4:** the live runs send GET requests to `boards-api.greenhouse.io` and
  `api.lever.co`. Each run writes a new `output/raw/<run_id>/` and
  `traces/trace_<run_id>.jsonl`, replaces `traces/checkpoint.json`, and updates the
  tracked files in `output/states/`. Writes to `config/` are refused unless you pass
  `--approve-config-write`; nothing in a normal run writes there.

## Exit codes (GATE.md 9.1, as amended by 9.9 and 9.10)

| Exit code | Status | Assignment term | Meaning |
| :---: | :--- | :--- | :--- |
| `0` | `SUCCESS` | finished | Every board in the config returned a verified observation. |
| `1` | `FATAL_SYSTEM_ERROR` | error | The loop could not keep its own contract: config unreadable or outside `config/`, a state file corrupt, a trace or state file could not be written, the same token listed under two providers, a denied loop-level file operation, or a bad command-line argument. |
| `2` | `PARTIAL_SUCCESS` | incomplete | Every reachable board was visited, but at least one did not produce a verified observation. Its job count is `null`. A run that includes the deliberate failures always ends here. |
| `3` | `BUDGET_EXCEEDED` | budget-exhausted | A budget (5 boards, 12 requests, 60 s) was exceeded, even if every board was visited. |

## What was actually run

**Live runs, 2026-11-10.** These were run by Claude Code with my approval of each command;
the full report is in [notes/real_runs_2026-11-10.md](notes/real_runs_2026-11-10.md).
- **Run `20261110T203826744076Z`** (20:38:26–20:38:30 UTC), `config/boards_with_failures.json`:
  - **Result:** `PARTIAL_SUCCESS`, exit code 2; 6 requests used.
  - **Boards:** cloudflare verified 468, palantir verified 304, datadog verified 395.
  - **Deliberate failures:** fail-notfound failed with `BOARD_NOT_FOUND` (404, not retried);
    fail-timeout failed with `TIMEOUT_EXHAUSTED` (two attempts, 1.5 s wait). Both had a `null` job count.
- **Run `20261110T203921572430Z`** (20:39:21–20:39:24 UTC), `config/boards.json`:
  - **Result:** `SUCCESS`, exit code 0; 3 requests used.
  - **Boards:** the same three verified with the same counts, and 0 added and 0 removed
    against the first run.
- **Saved output:** each run's trace and raw responses were copied to
  [output/real_run/](output/real_run/)`<run_id>/`. The originals are in `traces/` and
  `output/raw/`; the state after both runs is in `output/states/`.

**SEEDED finished-but-wrong demonstration, 2026-11-10 (offline).** Full write-up in
[output/demo/FINISHED_WRONG.md](output/demo/FINISHED_WRONG.md).
- **Input:** a **SEEDED** fixture, the real Cloudflare response with its last 18 jobs
  removed and `meta.total` left at 468.
- **Runs:** both used the tests' fake transport; no request went to the network.
  - **Branch `finished-wrong-demo`** (commit `e95d313`, not merged), where the GATE.md 4.2 count
    check is disabled: the run ended `SUCCESS`, exit code 0, reporting 450 jobs as verified.
  - **`main`:** the same input ended `PARTIAL_SUCCESS`, exit code 2, with `TRUNCATED_RESPONSE` and a `null` count.
- **Independent checker:** `check_independent.py` reported `WRONG` (18 postings missing) for
  the branch's trace, with exit status 1.

**Test runs.** The saved results are my own runs in `notes/` and `review/`:
- `tests_run_by_me_2026-11-09.txt`: 71 passed.
- `tests_after_narrow_fixes.txt`: 72 passed.
- `tests_after_policy.txt`: 1 failed (`IORouting`, before that test was fixed), 71 passed.
- `tests_after_policy_final.txt`: 88 passed.
- `review/01`: the review test failing before the credentials patch.
- `review/03`–`04`: the review test passing after the patch, then 89 tests and 4 subtests passing.

## Map of deliverables

| Path | What it is |
| --- | --- |
| [GATE.md](GATE.md) | The contract: exits, budgets, repeat rule, error policy, permission policy, boards, and the post-build amendments 9–9.11. |
| [BOUNDARY_TESTS.md](BOUNDARY_TESTS.md) | 17 permission-boundary predictions written before the policy existed, with the Actual and Match? results (all 17 match). |
| [review/](review/) | Credentials review: the failing test before the patch (`01`), the patch diff (`02`, empty in the current commit), the passing test (`03`) and the full suite (`04`) after it. `review/REVIEW_PACKET.md` is named in commits `893704f` and `45e85dc` but is **not in the repository** as of this draft. |
| [output/real_run/](output/real_run/) | Traces and raw responses of the two live runs on 2026-11-10. |
| [output/demo/](output/demo/) | The **SEEDED** finished-but-wrong demonstration: `FINISHED_WRONG.md`, both traces, the checker's output (`independent_check.txt`), the offline runner (`run_seeded_demo.py`), and my own run of the checker without arguments (`independent_check_run_by_me.txt`, which ended in an `IndexError`). |
| [check_independent.py](check_independent.py) | Standard-library-only checker that recounts a Greenhouse body and compares it with a trace. |
| SIGNOFF.md | My sign-off, including "Not checked". **Not in the repository** as of this draft. |
| FRICTIONAL.md | My Frictional log. **Not in the repository** as of this draft. |
| [SOURCES.md](SOURCES.md) | Endpoints, course chapters, and who wrote what (Claude Code, Claude chat, me). |
| [notes/](notes/) | Claude Code responses saved verbatim at my request (build report, discrepancy report, changed-tests explanation, review-patch response, live-run report), and my own test runs (`tests_*.txt`). `notes/unexpected_review_folder/` holds an earlier copy of the failing-test output, which differs from `review/01`. |
| [src/](src/), [tests/](tests/), [config/](config/) | The agent, its offline tests and fixtures, and the two board configs. |
| `output/raw/`, `output/states/`, `traces/` | What the agent itself wrote during the live runs. |

## What is not here, and what the agent never does

- **Not included:** no résumé, persona, credentials or conversation transcripts. `notes/` holds
  individual saved responses, not transcripts. The only credential-like strings are the
  fake `fakeuser` / `fakepass` written to a temporary netrc file by
  `tests/test_review_no_credentials.py`.
- **Never does:** the agent never applies to a job, submits a form, emails, messages or logs in.
  It sends only GET requests to `boards-api.greenhouse.io` and `api.lever.co` (GATE.md 9.5),
  follows no redirects, and sends no netrc credentials.
