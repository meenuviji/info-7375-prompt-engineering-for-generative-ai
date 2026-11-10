# Sources and contributions

## External sources

**Public job-board endpoints.** These are the only network endpoints the agent calls; both
are unauthenticated GET requests. URL templates are in `src/config.py`.

| Provider | Endpoint template | Boards used | Evidence |
| --- | --- | --- | --- |
| Greenhouse Job Board API | `https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true` | cloudflare, datadog; fail-notfound and fail-timeout (deliberate, invented tokens) | Live runs, 2026-11-10 (`output/real_run/`). The response is an object with a `jobs` list and `meta.total`. |
| Lever Postings API | `https://api.lever.co/v0/postings/{token}?mode=json` | palantir | Live runs, 2026-11-10. The response is a bare list with no total. |

**Endpoint documentation.** For these APIs it is published at
`https://developers.greenhouse.io/job-board.html` (Greenhouse) and
`https://github.com/lever/postings-api` (Lever). Claude Code did not re-check those links
when drafting this file; the dated evidence for how the endpoints behave is the saved live
responses.

**Course material.** INFO 7375 course Chapters 4–6.

## Contributions

### Claude Code (Anthropic's CLI agent)

**Working modes**
- **The loop build ran in auto mode:** the first build, committed by me as `d9590a3`.
- **After auto mode ended:** later steps ran with edits auto-accepted until I turned that off.
- **Commits:** Claude Code made commits `e0d441a` and `e2ff0aa`. It also made `0218bbd`,
  `4f32312`, `f9d0c47`, and `e95d313` (on the unmerged branch `finished-wrong-demo`). Each
  carries a `Co-Authored-By: Claude` trailer.
  - Git shows me as the author of every commit because they use this repository's git identity.
  - All other commits in this folder were made by me, including commits of files that Claude
    Code had written.

**File by file**

*Source code*
- `src/__init__.py`, `src/config.py`, `src/loop.py`, `src/policy.py`, `src/validate.py`:
  written by Claude Code.
  - Loop, budgets, repeat rule, error policy, trace and state handling: the initial build
    (`d9590a3`).
  - Comment and constant-check fixes: `1a97d7f`.
  - Permission policy, `--approve-config-write`, `POLICY_DENIED` handling: `bf53866`.
- `src/fetch.py`, `src/state.py`: adapted by Claude Code from my JS1 `agent/fetch.py` and
  `agent/state.py`. The `fetch.py` credentials patch (the `_no_auth` helper) was written
  by Claude Code and committed by me in `893704f`.

*Config and setup*
- `config/boards.json`, `config/boards_with_failures.json`: written by Claude Code, and set
  to the GATE.md 9.7 board list in `1a97d7f`.
- `requirements.txt`: written by Claude Code with JS1's pins; I added the `pytest` line (`22987ec`).
- `.gitignore`: written by Claude Code.

*Tests*
- `tests/__init__.py`, `tests/helpers.py`, `tests/test_loop.py`, `tests/test_validate.py`, and
  the hand-written fixtures in `tests/fixtures/` (with their README): written by Claude Code.
- `tests/test_boundary.py`: written by Claude Code (`e2ff0aa`). Each test asserts my
  prediction in `BOUNDARY_TESTS.md`.
- `tests/fixtures/SEEDED_truncated_cloudflare.json` and `.README.md`: made by Claude Code from
  the real Cloudflare response (`f9d0c47`).

*Boundary results, demo and runs*
- `BOUNDARY_TESTS.md`: Claude Code filled the Actual and Match? columns. Rows 1–14, 16 and 17
  are in `e2ff0aa`; the row 15 text is by Claude Code and was committed by me in `45e85dc`. The
  predictions, the reasoning and the Row 17 outcome are mine (see below).
- `check_independent.py`, `output/demo/run_seeded_demo.py`, `output/demo/FINISHED_WRONG.md`,
  `output/demo/finished_wrong_trace.jsonl`, `output/demo/gate_catches_trace.jsonl`,
  `output/demo/independent_check.txt`: written or produced by Claude Code (`f9d0c47`). The
  seeded bug itself is `e95d313` on `finished-wrong-demo`.
- `output/real_run/`: Claude Code ran both live runs on 2026-11-10, with my approval of each
  command, and copied their traces and raw responses here (`4f32312`). `output/raw/`,
  `output/states/` and `traces/` are what the agent wrote during those runs (I committed
  them in `b66e99a`).

*Notes and drafts*
- `notes/build_report_2026-11-09.md`, `notes/gate_discrepancies_2026-11-09.md`,
  `notes/changed_tests_2026-11-10.md`, `notes/review_patch_response_2026-11-10.md`,
  `notes/real_runs_2026-11-10.md`: Claude Code responses, saved verbatim at my request.
- GATE.md sections 1–5.1 as first committed (`0218bbd`): text written by me, written to the
  file and committed by Claude Code at my request.
- `README.md`, `SOURCES.md`: drafted by Claude Code at my request.

### Claude (claude.ai chat)

- Drafted GATE.md sections 9, 9.9, 9.10 and 9.11. I reviewed and accepted each one.
- Gave me the step-by-step plan I followed for this assignment.
- Gave me a written outline that I followed when writing `tests/test_review_no_credentials.py`.

### Written by me (Meena Periasamy)

- **GATE.md:** sections 1–8 (`667e5e7`, `0218bbd`, `3f48500`).
- **BOUNDARY_TESTS.md:** the predictions, my reasoning, and the row 17 decision (`fd0e047`).
- **The review:** `tests/test_review_no_credentials.py` (`c799546`) and my recorded runs in `review/` and `notes/tests_*.txt`.
- **Not in the repository** when this file was drafted (2026-11-10):
  - `review/REVIEW_PACKET.md`
  - `SIGNOFF.md`
  - `FRICTIONAL.md`
- **My JS1 code** that JS2 started from: `agent/fetch.py` and `agent/state.py`.
