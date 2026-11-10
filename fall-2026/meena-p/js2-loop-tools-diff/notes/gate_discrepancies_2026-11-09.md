2026-11-09

Raw Claude Code response, saved unedited

## Where the code disagrees with section 9

### 9.1 Run statuses
1. **A duplicate board token should exit 1, but the run continues.** `src/loop.py:101` raises an error only when one token appears under two providers. The same provider and token listed twice is allowed and becomes a repeat hit (`src/loop.py:346-357`). The `RepeatRule` tests rely on this kind of config (`tests/test_loop.py:211`).
2. **A fatal report still carries job counts.** 9.1 says exit 1 reports "No job counts". `fatal()` builds its report with `self.report(...)` (`src/loop.py:440`), and that includes every board finished so far, job counts and all. This matters when a later step fails, such as a disk write on board 2.
3. **`BUDGET_EXCEEDED` can be reported after every board was visited.** `src/loop.py:367` marks the time budget as exceeded if the last response arrived after 60 s. 9.1 limits exit 3 to a budget that ran out "before every board was visited".
4. **Field name:** failed boards are listed with `error_code` (`src/loop.py:408`), but 9.1 calls it the "error type".

### 9.2 Budgets
5. **The test that checks budgets against the table is incomplete.** `tests/test_loop.py:205-206` checks 60 s, 12 requests and 5 boards. It doesn't check `REQUEST_TIMEOUT_SECONDS = 10.0`. The 0.001 s value lives in the config file, not in a code constant; only `tests/test_loop.py:144` checks it, through the shipped config.
6. **A request with too little time left is started anyway.** 9.2 says never to start a request whose timeout plus any backoff would run past the remaining time; the run should end `BUDGET_EXCEEDED` instead. The code shortens the timeout to whatever time is left and sends the request (`src/loop.py:233-236`). `tests/test_loop.py:171-178` expects that behaviour: a 6 s timeout, then SUCCESS. The backoff check (`src/loop.py:274`) compares only the wait with the time left, not the wait plus the next request's timeout.
   - 9.2 is inconsistent with itself here. Its table row says the timeout is "never more than the seconds left", which describes shortening it. Its bullet says not to start the request at all. Which one wins?
7. **Stale comments:** `src/config.py:15-17` still cite "section 3" and "Not in GATE.md".

### 9.3 Repeat rule
8. **The key doesn't normalise the URL.** 9.3 wants a lowercase host and sorted query parameters. `Board.key` uses the raw URL string (`src/loop.py:55`). In practice the URLs come from fixed templates, so nothing breaks today.
9. **Trace event name:** the code writes `IDEMPOTENT_CACHE_HIT` with decision `REUSE_OBSERVATION` (`src/loop.py:350, 354`); 9.3 says `REPEAT_BLOCKED`. The test asserts the old name (`tests/test_loop.py:222`).
10. **The repeat result counts toward the run status.** The code reuses the earlier observation as that board's result (`src/loop.py:348-357`). 9.3 says only that the repeat isn't sent and is recorded.
    - **9.1 and 9.3 conflict.** Once a duplicate token is fatal, a config can never produce a repeat at board level, so 9.3's check could never run. Should the check move down to individual requests, or is it only a safety net?
11. **Tests built on a config that is now fatal.** All of `RepeatRule` (`tests/test_loop.py:210-251`) uses a config with cloudflare listed twice. That includes the tests that retries are exempt and that retries count against the request budget.

### 9.4 Error policy
12. **Error type names differ** (`src/config.py:57-63`). The tests assert the old names (`tests/test_loop.py:124, 263, 276, 282, 286, 327, 335, 373`).

    | Failure | GATE 9.4 | Code now |
    | --- | --- | --- |
    | Timeout | `TIMEOUT` | `TIMEOUT_EXHAUSTED` |
    | 5xx | `SERVER_ERROR` | `UPSTREAM_5XX_ERROR` |
    | 429 | `RATE_LIMITED` | `RATE_LIMITED_EXHAUSTED` |
    | 404 | `NOT_FOUND` | `BOARD_NOT_FOUND` |
    | Other 4xx | `CLIENT_ERROR` | `HTTP_ERROR` |
    | Connection error | `CONNECTION_ERROR` | `NETWORK_ERROR` |

13. **Connection errors aren't retried.** 9.4 says retry once after 1.5 s. The code marks them no-retry (`src/config.py:63`), and `tests/test_loop.py:325-327` expects one attempt.
14. **410 is treated as a generic error.** 9.4 groups it with 404 as `NOT_FOUND`. The code sends 410 to `HTTP_OTHER` (`src/loop.py:128, 136`).
15. **`HTTP_OTHER` catches more than other 4xx.** It also catches non-200 2xx, 1xx and anything above 599 (`src/loop.py:136`). 9.4 doesn't cover those.
16. **Malformed JSON gets the wrong code.** 9.4 says "malformed JSON or truncated body" is `TRUNCATED_RESPONSE`. The code gives `PARSE_SCHEMA_MISMATCH` to any non-JSON body that isn't cut off, such as an HTML page, a non-UTF-8 body or an empty body (`src/validate.py:116, 122`). The tests assert the old code (`tests/test_validate.py:64-66, 76-78`, `tests/test_loop.py:299-301`).
17. **The failed-board ledger entry has the wrong shape.** 9.4 and 5.3 want `status: "FAILED"` and an `error_type` field. The code writes `"status": "failed"` or `"verified"` and an `error_code` field (`src/loop.py:297-298`). `tests/test_loop.py:373` reads `error_code`.
18. **Kinds 9.4 doesn't list:** `REQUEST_ERROR` and `TRANSPORT_EXCEPTION` (`src/config.py:64-65`), for other `requests` errors and unexpected transport errors. Neither is retried.
19. **Backoff wording:** `src/config.py:53-54` and `src/loop.py:273` describe exponential backoff. With one retry the wait is the same as 9.4's fixed 1.5 s or 2.0 s, but the code contradicts 9.4's "not repeated backoff".

### 9.5 Permission policy (skipping the stubs in `src/policy.py`)
20. **Credentials could be sent.** 9.5 says no credentials, cookies or auth headers are ever sent. By default `requests` reads `~/.netrc` and the proxy environment variables, so it can attach an Authorization header without being asked (`src/fetch.py:56`). Disabling that needs a `requests.Session` with `trust_env = False`.
21. **`--approve-config-write` doesn't exist.** `main()` defines only `--config` (`src/loop.py:488`).
22. **Every denial is fatal.** A `PolicyViolation` is re-raised as a loop-level error with exit 1 (`src/loop.py:221-222`), but 9.1's list of exit-1 causes doesn't include policy denials. 9.5 also wants every denial in the trace with the rule that denied it. A denial that happens before the trace exists, such as reading the config, isn't traced, and the trace line written later doesn't name a rule.
23. **Any config path is accepted.** `--config` takes an absolute path anywhere on disk (`src/loop.py:466`). Once enforcement is in place, the read check would deny anything outside `config/`, `output/` and `traces/`.

### 9.6 Wrong versions the tests must catch
24. **#1–4 have no tests.** Host and path checks can't be tested until the policy is enforced, as expected.
25. **#5 and #12 are tested only through the duplicate-board config** (`tests/test_loop.py:211, 227-237`), which 9.1 now makes fatal. The `Board.key` check at `:213-215` and the request-budget test at `:160-165` don't depend on that config.
26. **#15 is only half covered.** `tests/test_loop.py:417-424` proves an existing trace isn't overwritten, but it passes a fixed run id. Nothing tests that two run ids generated in the same second differ (`utc_timestamp` in `src/fetch.py`).
27. **#6–11, #13, #14 and #16 have tests that pass today.** #11 is the one that also catches a code change: a bad argument must exit 1, not 2.

### 9.7 Boards
28. **`config/boards.json:4-6`** lists cloudflare, datadog and automattic (Lever). 9.7 wants cloudflare, palantir (Lever) and datadog, in that order.
29. **`config/boards_with_failures.json:4-8`** has automattic instead of palantir, and `empty-verified` instead of `fail-notfound` (Greenhouse, deliberate). `fail-timeout` with a 0.001 s timeout already matches.
30. **`tests/test_loop.py:143`** expects the deliberate tokens to be `empty-verified` and `fail-timeout`. The offline tests also use `automattic` as a fixture token (`tests/test_loop.py:16-17`, and the `boards =` lines at `:211, 254, 356`). Nothing breaks, but it no longer matches the board list.

### 9.8 Ratified build decisions
31. **No disagreements.** All eight ratified rows match the code:
    - `meta.total < len(jobs)` and a missing `meta.total` (`src/validate.py`)
    - an empty Lever list (`src/validate.py`)
    - a token under two providers (`src/loop.py:101`)
    - a baseline diff of `null` (`src/state.py:64-65`)
    - no state for a board cut off by a budget
    - `trace_<run_id>.jsonl`
    - a fatal error before the trace exists leaving no files

## Sections 5–8, which 9 doesn't replace
32. **State file schema (5.2):**
    - **Top level:** 5.2 wants `last_updated_at` and `last_status`. `next_state` writes `schema_version`, `provider`, `active_job_ids` and `ledger` (`src/state.py:79-85`).
    - **Ledger entries:** 5.2 wants status `SUCCESS` and the counts as `added_count`, `unchanged_count` and `removed_count`. The code writes `verified` and a nested `diff` object (`src/loop.py:294-305`).
    - **Ids:** 5.2's example shows ids as strings (`"1001"`). The code stores Greenhouse ids as integers.
33. **Section 7 lists `output/diffs/` and `output/jobs/`.** The code writes neither. It also writes `output/raw/` and `traces/malformed/`, which section 7 doesn't name; 9.5's folder-level rules allow both.

The questions I need you to decide are in items 6 and 10.
