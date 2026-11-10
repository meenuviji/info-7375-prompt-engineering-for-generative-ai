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
