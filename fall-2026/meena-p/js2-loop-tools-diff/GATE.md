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
