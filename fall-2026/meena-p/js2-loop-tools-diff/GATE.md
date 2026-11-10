# GATE.md — Job-Search Agent 2 (JS2): Loop, Tools & Diff

## 1. Overview & Objectives
Job-Search Agent 2 (JS2) executes an automated, multi-source polling cycle across job boards. It verifies payload integrity, normalizes job data, computes diff sets (added, unchanged, removed) against prior snapshots, maintains per-board state persistence, and logs immutable traces.

---

## 2. CLI Execution & Process Exit Codes
The runner MUST terminate with standard exit codes reflecting run status:

| Exit Code | Semantic Status | Description |
| :---: | :--- | :--- |
| **`0`** | `SUCCESS` | All configured boards processed, verified, diffed, and written. |
| **`1`** | `FATAL_SYSTEM_ERROR` | Unhandled runtime exception, configuration load failure, or CLI arg error. |
| **`2`** | `PARTIAL_SUCCESS` | Execution completed, but one or more target boards encountered non-fatal failures or verification errors. |
| **`3`** | `BUDGET_EXCEEDED` | Exceeded execution time limit (60s) or cumulative request budget (12 requests). |

*(Note: Exit code scheme `0/1/2/3` supersedes any legacy references).*

---

## 3. Budgets & Quotas
Hard constraints enforced across the execution lifecycle:
- **Global Runtime Limit:** Max 60 seconds total execution time.
- **Max HTTP Requests:** 12 requests per run across all boards.
- **Per-Board Retry Exemption:** HTTP retries (429/5xx with exponential backoff) count toward the 12-request budget, but idempotent repeated status checks do not violate single-request board policies.

---

## 4. Verification & Payload Validation

### 4.1. Valid Empty Lists vs. Suspicious Payloads
- **Legitimate Zero (`0` Jobs):** An empty list (`[]` or `{"jobs": []}`) is valid **ONLY** if HTTP status is `200 OK`, JSON parsing succeeds, and metadata explicitly matches 0 entries (`meta.total == 0` or total count key is 0).
- **Suspicious Empty:** An empty list received when metadata implies jobs exist, or accompanied by non-200/malformed status, must trigger `SUSPICIOUS_PAYLOAD` and mark the board failed.

### 4.2. `TRUNCATED_RESPONSE` Definition
A response is flagged as `TRUNCATED_RESPONSE` under either of two conditions:
1. **Structural/Syntax Incompletion:** The JSON body abruptly terminates mid-stream or fails syntax closure (unclosed brackets/braces).
2. **Metadata Count Mismatch:** The parsed job array length is strictly less than the advertised header/envelope count (`meta.total > len(jobs)`).

---

## 5. Per-Board State Architecture & Diffing

### 5.1. File Path & Structure
Per-board state is stored at:
```text
output/states/{board_token}.json
```

### 5.2. Schema: Unified Ledger + ID Snapshot
State files contain both the current verified ID set and historical audit run metadata:
```json
{
  "board_token": "cloudflare",
  "last_updated_at": "2026-11-09T20:25:00Z",
  "last_status": "SUCCESS",
  "active_job_ids": ["1001", "1002", "1005"],
  "ledger": [
    {
      "timestamp": "2026-11-09T20:25:00Z",
      "status": "SUCCESS",
      "added_count": 1,
      "unchanged_count": 2,
      "removed_count": 0
    }
  ]
}
```

### 5.3. Diff Evaluation Rules
- **Diff Computation:** Compare incoming active IDs with `active_job_ids` from the prior state.
  - `added`: $ID_{new} \setminus ID_{old}$
  - `unchanged`: $ID_{new} \cap ID_{old}$
  - `removed`: $ID_{old} \setminus ID_{new}$
- **Failed Boards:** If a board fails verification or network fetch, **do not overwrite `active_job_ids`**. Append a run record to `ledger` indicating failure (`status: "FAILED"`, `error_type: "..."`) leaving existing job snapshot intact for future diff comparisons.

---

## 6. Checkpoints & Trace Immutability
- **Immutable Traces:** Run execution traces are strictly append-only and written to timestamped files:
  ```text
  traces/trace_{timestamp}.json
  ```
- **Frozen Checkpoint Pointer:** A copy or atomic update of the latest run state is written to:
  ```text
  traces/checkpoint.json
  ```
  *(Overwriting `traces/checkpoint.json` is permitted strictly as the designated pointer to the latest checkpoint; individual session traces under `traces/trace_*.json` MUST never be overwritten).*

---

## 7. File System Access Boundaries
The agent is explicitly authorized to interact with the following directory scopes:
- `output/` — Read/Write (`output/states/{board_token}.json`, `output/diffs/`, `output/jobs/`).
- `traces/` — Read/Write (`traces/trace_*.json`, `traces/checkpoint.json`).
- `config/` — Read-only.
- `personas/` — Read-only.

---

## 8. Board Configuration Suite (5 Boards)
Execution runs against a 5-board target matrix:

| Slot | Board Token | ATS Type | Purpose | Expected Outcome |
| :---: | :--- | :--- | :--- | :--- |
| **1** | `cloudflare` | Greenhouse | Real Active Board | Returns valid active jobs |
| **2** | `datadog` | Greenhouse / Custom | Real Active Board | Returns valid active jobs |
| **3** | `automattic` | Lever | Real Active Board | Returns valid active jobs |
| **4** | `empty-verified` | Mock / Test ATS | Verified Empty | Valid HTTP 200, 0 jobs (`meta.total: 0`) |
| **5** | `fail-timeout` | Mock / Network Inject | Deliberate Failure | Forced timeout (0.001s or 504 Gateway Timeout) |

---

## 9. Amendment — 2026-11-09 (after the build)

*Drafted by Claude (claude.ai chat) on 2026-11-09, from my earlier gate sections, Claude Code's build report (notes/build_report_2026-11-09.md), and checks I ran by hand. Reviewed and accepted by Meena Periasamy. Sections 1–8 were written before any code (commits 667e5e7, 0218bbd). This section was written after the loop was built (d9590a3). Where this section and sections 1–8 disagree, this section wins.*

### 9.1. Run statuses in the assignment's terms

| Exit code | My status | Assignment term | When | What the run reports |
| :---: | :--- | :--- | :--- | :--- |
| `0` | `SUCCESS` | finished | Every board in the config returned a verified observation. | Per-board job counts and diffs, the trace path, elapsed seconds, requests used. |
| `1` | `FATAL_SYSTEM_ERROR` | error | The loop cannot keep its own contract: config unreadable, a state file corrupt, a trace or state file cannot be written, a duplicate board token, or a bad command-line argument. | The error and its traceback. No job counts. |
| `2` | `PARTIAL_SUCCESS` | incomplete | Every reachable board was visited, but at least one did not produce a verified observation. | Verified boards as for `0`. Each failed board listed with its error type and a job count of `null`. |
| `3` | `BUDGET_EXCEEDED` | budget-exhausted | A budget in 9.2 ran out before every board was visited. | What was observed before the limit, plus the list of boards never visited. |

- A run that stops is not a run that succeeded. Exit `0` is allowed only when every board is verified.
- The `deliberate: true` flag on a board is a label in the trace. It never changes a run's status. A run that includes the deliberate failures always ends `PARTIAL_SUCCESS`.
- Python's argparse exits with 2 by default on a bad argument, which would be misreported as `PARTIAL_SUCCESS`. The runner must catch argument errors and exit `1`.

### 9.2. Budgets (replaces section 3)

| Budget | Limit | Reason |
| :--- | :--- | :--- |
| Boards per run | 5 | 3 real boards and 2 deliberate failures (9.7). |
| HTTP requests per run | 12 | Worst case is 9: 3 real boards × 2 attempts, the 404 board × 1, the timeout board × 2. That leaves headroom without letting a retry loop run away. |
| Wall-clock seconds per run | 60 | Enough for a normal run. A slow network can still exhaust it, and the run must then say `BUDGET_EXCEEDED`, not fake success. |
| Per-request timeout | 10 s, never more than the seconds left | One slow board can't use up the whole run. |
| Deliberate timeout board | 0.001 s | Forces a timeout on purpose. |

- **Who may change a budget:** only I may, by editing this section in a commit whose message gives the reason. The agent cannot change budgets: config is read-only to it (9.5), and the code's budget constants must equal this table. A test checks that they match.
- A request is never started if its timeout plus any backoff would run past the remaining seconds. The run ends `BUDGET_EXCEEDED` instead.
- The line in section 3 about "idempotent repeated status checks" is withdrawn. The repeat rule is 9.3.

### 9.3. Repeat rule

- **The same action** means a request with the same provider, board token, HTTP method, and normalized URL (lowercased host, query parameters sorted), within one run.
- **What the loop does:** it does not send the repeat. It records `REPEAT_BLOCKED` in the trace, and the blocked repeat does not use the request budget.
- **Retries are the one exception:** a retry that the error policy (9.4) authorizes is allowed through. It is capped by 9.4's retry count and counts against the request budget.
- The attempt number is **not** part of the "same action" key. If it were, any bug that increased the counter would bypass the rule.
- The repeat record lasts one run only. Fetching the same board again on the next run is the point of a watcher.

### 9.4. Error policy (replaces the retry wording in section 3)

A failure belongs to its board. The loop records it and moves on to the next board. Only the loop-level failures in 9.1 (exit `1`) stop the run.

| Failure | Error type | Retry? | Why | Then |
| :--- | :--- | :---: | :--- | :--- |
| Timeout | `TIMEOUT` | Once, after 1.5 s | Usually transient. A second failure is information, not bad luck. | Board failed. |
| Connection error or DNS failure | `CONNECTION_ERROR` | Once, after 1.5 s | Same reasoning as a timeout. | Board failed. |
| HTTP 5xx or 429 | `SERVER_ERROR` / `RATE_LIMITED` | Once, after 2.0 s | Server-side and often transient. One retry, not repeated backoff, so the request budget stays predictable. | Board failed. |
| HTTP 404 or 410 | `NOT_FOUND` | No | Permanent. Retrying a wrong board name only spends budget. | Board failed. |
| Other 4xx | `CLIENT_ERROR` | No | The request itself is wrong, so sending it again won't help. | Board failed. |
| 3xx redirect | `REDIRECT_REFUSED` | No | A redirect could lead to a host off the allow-list (9.5). Redirects are never followed. | Board failed. |
| Malformed JSON or truncated body | `TRUNCATED_RESPONSE` | No | The same server is likely to return the same body again. | Board failed. Raw body saved. |
| `meta.total > len(jobs)` | `TRUNCATED_RESPONSE` | No | As section 4.2. | Board failed. |
| Empty list without metadata proving 0 | `SUSPICIOUS_PAYLOAD` | No | As section 4.1. | Board failed. |
| Wrong shape, missing `id`, or the count mismatches listed in 9.8 | `PARSE_SCHEMA_MISMATCH` | No | A structural problem, not a transient one. | Board failed. |

**What "board failed" means, every time:**
- The job count is `null`. A failure is never turned into a value such as 0.
- `active_job_ids` is not overwritten, as in section 5.3.
- A `FAILED` ledger entry is added with its error type.
- The raw response is saved if there was one.
- The run ends `PARTIAL_SUCCESS` at best.

**Escalation:** the agent never contacts anyone (9.5). Escalation means the failure is in the run's status, the run report, and the trace, and I review it.

### 9.5. Permission policy (extends section 7)

Enforced in code, in `src/policy.py`, through `SecurityPolicy.validate_network_request`, `validate_file_read`, and `validate_file_write`. Every check is **default deny**. Every denial is recorded in the trace with the rule that denied it. A prompt is not enforcement.

**Network**
- Allowed hosts, matched exactly after the URL is parsed, never by substring or prefix: `boards-api.greenhouse.io` and `api.lever.co`.
- HTTPS only. GET only. Redirects are never followed.
- No credentials, cookies, or authorization headers are ever sent.

**Files**
- Every path is resolved to a real absolute path, following `..` and symlinks, before it is checked. Whether a path is inside an allowed folder is decided by comparing path components, never by string prefix. So `output-evil/` is not inside `output/`.
- Read is allowed in `config/`, `output/`, and `traces/`.
- Write is allowed in `output/` and `traces/`.
- Existing trace files under `traces/` are never overwritten, as in section 6. `traces/checkpoint.json` is the only file there that may be replaced.
- **Approval-required write:** a write to `config/` (which holds the board list) needs my approval, given by running with `--approve-config-write`. Without that flag it is denied. No test ever prompts for approval interactively.
- Any write outside `output/`, `traces/`, and `config/` is denied, **even with approval**.
- `personas/` is removed from section 7. JS2 does not use personas; they stayed in JS1.

**Never, under any input**
- Apply to a job, submit a form, email, message, or log in.
- Send any request other than GET.
- Contact a host that isn't on the allow-list.

### 9.6. Wrong versions my tests must catch

1. A host check by substring or prefix, which lets `boards-api.greenhouse.io.evil.com` through.
2. A path check by string prefix, which lets `output-evil/` through.
3. A path check that doesn't resolve symlinks, so a link inside `output/` escapes.
4. A path check that doesn't normalize `..`.
5. The attempt number added to the repeat key, which lets retries bypass the repeat rule.
6. Retrying a 404.
7. A failed board reported with a job count of 0.
8. A failed board overwriting `active_job_ids`.
9. A run with a failed board exiting `0`.
10. Emptiness judged by response size instead of structure and metadata.
11. A bad command-line argument exiting `2`, and so reported as partial success.
12. A request budget counted per board, or retries left out of the count.
13. A truncated response (`meta.total > len(jobs)`) accepted as complete.
14. The `deliberate` flag changing a run's status.
15. A trace overwritten by a second run in the same second.
16. Paths resolved against the current directory instead of the project root.

### 9.7. Boards (replaces section 8)

| Slot | Board token | ATS | Purpose | Expected outcome | Checked |
| :---: | :--- | :--- | :--- | :--- | :--- |
| 1 | `cloudflare` | Greenhouse | Real board | Verified jobs | Used in JS1 |
| 2 | `palantir` | Lever | Real board (the second ATS) | Verified jobs | By hand, 2026-11-09: HTTP 200, list of 304 jobs |
| 3 | `datadog` | Greenhouse | Real board | Verified jobs | **Pending.** I check it by hand before the real run. If the check fails, this board is replaced by a further amendment. |
| 4 | `fail-notfound` | Greenhouse | Deliberate failure (permanent) | `NOT_FOUND`, no retry | Invented token, on purpose |
| 5 | `fail-timeout` | Greenhouse | Deliberate failure (transient) | `TIMEOUT` after one retry | Invented token, 0.001 s timeout |

- `automattic` is removed. When I checked by hand, `api.lever.co/v0/postings/automattic` returned 404.
- `empty-verified` is removed from the live boards. It's an invented token that would return 404, not a verified 0. The verified-zero path in section 4.1 is covered by an offline fixture test only.
- `config/boards.json` holds slots 1–3. `config/boards_with_failures.json` holds all five.

### 9.8. Decisions the build made that sections 1–8 did not cover

Claude Code made these during the build (notes/build_report_2026-11-09.md). Each one is now a gate decision.

| Decision | Ratified? | Reason |
| :--- | :---: | :--- |
| `meta.total < len(jobs)` is `PARSE_SCHEMA_MISMATCH` | Accepted | More jobs than the board advertises means the count can't be trusted. |
| A Greenhouse response with no `meta.total` is `PARSE_SCHEMA_MISMATCH` | Accepted | Without the total, the truncation check in 4.2 can't run. |
| An empty Lever list is always `SUSPICIOUS_PAYLOAD`, never a verified 0 | Accepted | Lever sends no count, so section 4.1's metadata proof is impossible. |
| State files are named by board token only. The same token under two providers is a config error (exit `1`). | Accepted | Matches section 5.1, and two boards can never share one state file. |
| A board's first run is a baseline, with diff `null` | Accepted | Without earlier ids, every posting would otherwise count as "added". |
| A board cut off by a budget writes no state | Accepted | Same reasoning as a failed board in 5.3. |
| Trace file is `traces/trace_<run_id>.jsonl`, one JSON line per event (replaces section 6's `trace_{timestamp}.json`) | Accepted | One line per event can be appended as the run goes. The run id prevents same-second collisions (9.6 #15). |
| A fatal error before the trace exists leaves no files; the report goes to stdout/stderr only | Accepted | If the trace can't be created, there's nowhere safe to write. Listed under "Not checked" in the sign-off. |

### 9.9. Corrections after comparing the code with section 9 (2026-11-09)

*Drafted by Claude (claude.ai chat) from Claude Code's comparison (notes/gate_discrepancies_2026-11-09.md); reviewed and accepted by Meena Periasamy. Items 1, 6 and 10 of that report were contradictions in Claude's draft of section 9. Where 9.9 and earlier sections disagree, 9.9 wins.*

**Duplicate boards and the repeat rule (report items 1, 10, 11)**
- Only the same token listed under two different providers is a config error (exit `1`), as 9.8 says. The rule in 9.1 is narrowed to that case.
- The same provider and token listed twice is allowed. The second one is a repeat under 9.3. It is not sent, it is recorded as `IDEMPOTENT_CACHE_HIT` with decision `REUSE_OBSERVATION`, and it reuses the first observation. A repeat can never make the run's status better or worse than the first observation already made it.

**Statuses (items 2, 3)**
- An `error` report may list boards verified before the fatal error, with their counts. They are real observations. The `error` status means the run as a whole cannot be trusted.
- Exit `3` applies whenever any budget was exceeded, even if every board was visited.

**Time left in the budget (item 6)**
- When less time is left than the normal 10 s request timeout, the request is sent with its timeout shortened to the time left. The 9.2 bullet saying never to start such a request is withdrawn.
- Known weakness: if a shortened request times out, the trace records the board as `TIMEOUT_EXHAUSTED`, although the budget may be the real cause. This is listed under Not checked in my sign-off.

**Repeat key (item 8)**
- The repeat key uses the URL exactly as built from the provider's template, not a normalized URL. Every URL is built from fixed templates, so the same board always gives the same string. URL normalization is not implemented, and it is listed under Not checked.

**Error types and retries (items 12–18)**

The code's names are adopted:

| Failure | Error type | Retry? |
| :--- | :--- | :---: |
| Timeout | `TIMEOUT_EXHAUSTED` | Once, after 1.5 s |
| HTTP 5xx | `UPSTREAM_5XX_ERROR` | Once, after 2.0 s |
| HTTP 429 | `RATE_LIMITED_EXHAUSTED` | Once, after 2.0 s |
| HTTP 404 | `BOARD_NOT_FOUND` | No |
| HTTP 410, other 4xx, non-200 2xx, 1xx, or a status above 599 | `HTTP_ERROR` / `HTTP_OTHER` | No |
| Connection error or DNS failure | `NETWORK_ERROR` | **No.** Changed from 9.4. A refused connection or failed DNS lookup rarely clears in 1.5 s, and timeouts already cover the transient case. |
| Other `requests` error, or an unexpected transport error | `REQUEST_ERROR` / `TRANSPORT_EXCEPTION` | No |
| JSON cut off mid-structure, or `meta.total > len(jobs)` | `TRUNCATED_RESPONSE` | No |
| A body that isn't JSON (an HTML page, non-UTF-8, empty), wrong shape, missing `id`, or the count cases in 9.8 | `PARSE_SCHEMA_MISMATCH` | No |

- With one retry, each wait is a single fixed 1.5 s or 2.0 s, not repeated backoff.
- Every failure in this table still means everything "board failed" means in 9.4: a `null` count, `active_job_ids` untouched, a failed ledger entry, and the run at best `PARTIAL_SUCCESS`.

**Field names and state schema (items 4, 17, 32)**
- Failed boards and ledger entries use the field `error_code`, not "error type". Ledger status values are `verified` and `failed`, not `SUCCESS` and `FAILED`.
- A state file holds `schema_version`, `board_token`, `provider`, `active_job_ids` and `ledger`. Each ledger entry carries a nested `diff` object instead of separate count fields. Section 5.2's example is illustrative only.
- Ids keep their provider's type: integers for Greenhouse, strings for Lever.

**Folders (item 33)**
- The agent writes `output/states/`, `output/raw/`, `traces/` and `traces/malformed/`. Section 7's `output/diffs/` and `output/jobs/` are not used and are withdrawn.

**Boards (items 28–30)**
- Datadog was checked by hand on 2026-11-09: a Greenhouse board returning 400 jobs with `meta.total` 400. It is confirmed for slot 3 in 9.7.
- Offline test fixtures may use invented tokens, such as `automattic`, as test names. Only the live configs must match 9.7.

**Moved to the permission-policy step (items 20–23)**
- Not sending `~/.netrc` or proxy-environment credentials, the `--approve-config-write` flag, policy denials, and restricting `--config` to `config/` are implemented and tested in the permission-policy step. Each gets a prediction written before the code.

### 9.10. Policy denials (decided 2026-11-09, before the policy was implemented)

- A board whose URL fails the network policy (host off the allow-list, not HTTPS, or not GET) is a board failure: error code `POLICY_DENIED`, no request sent, a `null` count, `active_job_ids` untouched. The run continues and ends at best `PARTIAL_SUCCESS` (exit 2). Reason: failure isolation, as in 9.4; one bad config line must not hide the other boards.
- A denial of a file operation the loop itself needs (reading the config, writing a trace or state file) is loop-level: exit `1`.
- Every denial is recorded in the trace with the rule that denied it, when a trace exists. A denial that happens before the trace exists goes to stderr, as in 9.8.
- Note: this section was meant to be committed with my boundary predictions in fd0e047, but the append had not been run. It is added here, still before any policy code.
