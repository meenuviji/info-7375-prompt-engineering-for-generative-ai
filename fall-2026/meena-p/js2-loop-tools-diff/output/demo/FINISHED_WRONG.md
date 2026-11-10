# A finished-but-wrong run: truncated Greenhouse response (SEEDED, offline)

> **This whole demonstration is a SEEDED, OFFLINE run.** The input is a real Cloudflare
> response that was deliberately damaged. The broken loop exists only on the unmerged branch
> `finished-wrong-demo`. Every run below used the tests' fake transport, and no request went
> to the network. None of the numbers here describe Cloudflare's live board.

## 1. How the fixture was seeded

- **Source:** `output/real_run/20261110T203921572430Z/raw/greenhouse_cloudflare_attempt1.body`,
  the real response from the live run of 2026-11-10, 20:39:21 UTC
  (SHA-256 `9a43d1647f15b57c4ad8a522f04fe9e504c369c4e2f0b0bae62ba3bdea5b585d`). It has 468
  jobs and `meta.total` 468.
- **Seeded file:** `tests/fixtures/SEEDED_truncated_cloudflare.json`. The **last 18 entries of
  `"jobs"` were removed** and `meta.total` was left at **468**, so the body holds 450 jobs.
  The removed ids and the re-serialization details are in
  `tests/fixtures/SEEDED_truncated_cloudflare.README.md`.
- **Why it matters:** this is what a response cut short in transit or by the server looks
  like. It is still valid JSON with the right shape, but some postings are missing. GATE.md
  4.2 (case 2) and the 9.9 table class it as `TRUNCATED_RESPONSE`.

## 2. The demo branch: `finished-wrong-demo` (commit `e95d313`, not merged)

- **The change:** in `src/validate.py`, only the `meta.total > len(jobs)` check is commented out,
  marked `SEEDED REPRODUCTION ... never merge`. Every other check is unchanged.
- **The run:**
  `.venv/bin/python output/demo/run_seeded_demo.py tests/fixtures/SEEDED_truncated_cloudflare.json output/demo/finished_wrong_trace.jsonl`

What the branch reported (trace in `output/demo/finished_wrong_trace.jsonl`):

| Field | Value |
| --- | --- |
| Status | **`SUCCESS`** |
| Process exit code | **0** |
| Board outcome | cloudflare `verified` |
| Job count | **450** |
| Error code | none |
| Observations | `meta_total` 468, `jobs_in_body` 450 |
| Requests | 1 |

It finished cleanly and it is wrong. The run says "450 verified postings, success". The
evidence that 18 are missing (`meta_total` 468 against `jobs_in_body` 450) sits in its own
trace, and nothing acted on it. A watcher built on this would also have recorded the 18
missing ids as removed postings in the next diff.

## 3. The independent checker's verdict

`output/demo/independent_check.txt`, from
`.venv/bin/python -I check_independent.py tests/fixtures/SEEDED_truncated_cloudflare.json output/demo/finished_wrong_trace.jsonl`
(exit status 1):

```text
jobs in body:         450
meta.total:           468
count trace reported: 450
trace error_code:     None
run status (RUN_END): SUCCESS
verdict: WRONG - the run reported 450 jobs as a verified count and ended SUCCESS, but the body advertises 468: 18 postings are missing from the response. A truncated response was accepted as complete.
```

## 4. Why the checker is independent

- **Imports:** `check_independent.py` imports only the Python standard library (`json`, `sys`).
  It imports nothing from `src/` or `tests/`, so it doesn't share the loop's validation code
  and can't inherit the loop's bug.
- **Isolated interpreter:** it is run with `python -I` (isolated mode). The script's folder and
  the current directory are not on the import path, and `PYTHON*` environment variables are
  ignored, so not even an accidental project import is possible.
- **Inputs:** it reads only two files, the raw body and the trace. It recounts `len(jobs)` and
  reads `meta.total` from the body itself, and compares those with what the trace claims.
- **What it trusts:** only the JSON format of the two files. It does not trust the loop's status,
  job count or observations; it treats them as claims to check.

## 5. What the real loop does with the same input (`main`)

The same fixture, the same runner and the same fake transport, on `main`
(trace in `output/demo/gate_catches_trace.jsonl`):

| Field | Value |
| --- | --- |
| Status | **`PARTIAL_SUCCESS`** |
| Process exit code | **2** |
| Board outcome | cloudflare `failed` |
| Job count | **null** |
| Error code | **`TRUNCATED_RESPONSE`** |
| Observations | `truncation: count`, `meta_total` 468, `jobs_in_body` 450 |
| Requests | 1 (no retry, as 9.9 specifies) |

This follows GATE.md 4.2 and 9.9: the board fails, no count is reported, and in a real run
`active_job_ids` would be left untouched, so the next diff isn't corrupted. Run on this
trace, the same independent checker prints **`CAUGHT`** and exits 0. That output was shown
on screen but not saved.

## 6. This check exists only for Greenhouse

- **Greenhouse** sends `meta.total`, so the loop can compare the advertised count with the
  jobs actually in the body (GATE.md 4.2).
- **Lever sends no total.** Its response is a bare list, so there is nothing to compare against.
  A Lever response cut short in the same way would still be valid JSON, would pass every
  structural check, and would be reported as a verified count. GATE.md 9.8 accepts the
  consequence for empty lists: an empty Lever list is always `SUSPICIOUS_PAYLOAD`, never a
  verified 0. For a non-empty but short Lever list, JS2 has no defense.
- The same is true of this independent checker. It could only flag the Greenhouse case
  because the body carried its own total.

## 7. Files

- `tests/fixtures/SEEDED_truncated_cloudflare.json` and `.README.md`: the seeded input.
- `output/demo/run_seeded_demo.py`: the offline runner, which uses `tests/helpers.py`'s
  `Sandbox` and `ScriptedTransport` in a temporary root, so the real `output/states/` is never touched.
- `output/demo/finished_wrong_trace.jsonl`: the trace from the demo branch.
- `output/demo/independent_check.txt`: the checker's output on that trace.
- `output/demo/gate_catches_trace.jsonl`: the trace from `main`.
- `check_independent.py`: the independent checker.
- Branch `finished-wrong-demo` (`e95d313`): the seeded bug. It is local only, not merged and not pushed.
