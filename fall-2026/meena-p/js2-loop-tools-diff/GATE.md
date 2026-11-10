# GATE.md — Job-Search Agent 2

Written by Meena Periasamy before any code was generated for JS2. Date: November 9, 2026

## Exits

| Exit status | When it happens | What the run reports |
| --- | --- | --- |
| finished | All scheduled target boards have been queried; raw payload byte streams are written to disk; schema parsing succeeded for every response; zero unhandled network or permission exceptions occurred. | Total target boards visited, total valid postings harvested per board, aggregate run duration, and explicit integrity hashes of the saved raw response files. |
| incomplete | An unrecoverable per-board failure occurred (such as a 404 target, a malformed JSON schema, or a non-retryable network fault) that halted further ingestion without exhausting system resource budgets. | Boards successfully processed before interruption, identity and raw status code of the failing board, exact timestamp of abort, and partial records saved. |
| budget-exhausted | The run hit any single ceiling: `max_boards` reached, `max_requests` depleted, or elapsed wall-clock time exceeded `max_seconds`. | The specific budget limit tripped, count of boards processed vs. queued, total requests issued, elapsed wall-clock seconds, and frozen checkpoint state. |
| error | An unhandled system catastrophe occurred outside standard API responses (e.g., security sandbox breach attempt, disk write failure, or out-of-memory exception). | Raw exception traceback, failing internal operation/subsystem, boundary state at crash, and immediate diagnostic notice. |

A run that stops is not a run that succeeded: An execution that halts without throwing an unhandled exception is not successful unless every scheduled target in the batch exists in the verified observations dictionary with a validated schema and written raw response. Merely terminating clean with return code 0 or an empty exception stack while skipping targets or reporting fabricated fallbacks counts strictly as `incomplete` or `error`.

## Budgets

* Max boards per run: 4 (Cloudflare, Stripe, Figma, and 1 deliberate test failure board).
* Max HTTP requests per run: 8 (accommodates 4 initial board fetches plus up to 1 legitimate retry per transient failure).
* Max wall-clock seconds per run: 30.0 seconds (prevents hangs during stalled DNS resolution or slow socket transfers).
* Who may change these: Meena Periasamy only. Budgets are immutable code constants in `src/config.py`. Modifying any limit requires a signed engineering decision record committed directly to Git; Claude Code and the automated runtime are strictly forbidden from adjusting them dynamically.

## Repeat rule

* "The same action" means: An outgoing network request sharing an identical tuple of `(provider_name, board_token, http_method, canonical_url)`.
* When the loop sees a repeat, it: Skips dispatching the HTTP request entirely, records an `IDEMPOTENT_CACHE_HIT` event in the execution trace, and yields the previously recorded observation without consuming an HTTP request budget counter.

## Error policy

| Failure | Retry? | How many | Why retrying here is sound (or not) | Then |
| --- | --- | --- | --- | --- |
| Timeout | Yes | 1 | Sound: Socket-level stalls or network blips are frequently transient; a brief backoff window often resolves congested transport. | Wait 1.5s with linear backoff. If it fails a second time, log `TIMEOUT_EXHAUSTED`, write failure metadata to the trace, and halt/mark as `incomplete`. |
| 5xx | Yes | 1 | Sound: Upstream server load spikes or transient gateway timeouts (502/503/504) can clear immediately on standard ATS endpoints. | Wait 2.0s. If the retry fails, log `UPSTREAM_5XX_ERROR`, record the exact status code returned, and advance to next board if isolated. |
| 404 / unknown board | No | 0 | Not sound: A 404 response on an ATS public endpoint indicates an invalid token or deleted board. Retrying sends an identical failing request pointlessly. | Record `BOARD_NOT_FOUND` with HTTP 404 status code, record empty observation entry with failure flag, and proceed to subsequent boards in the queue. |
| 200 with empty job list | No | 0 | Not sound: The server answered authoritatively with valid syntax. Retrying will yield the exact same semantic response. | Run independent payload length check. If byte count > 300 bytes, flag as `SUSPICIOUS_EMPTY_PAYLOAD`; otherwise record verified 0 jobs. |
| 200 with malformed body | No | 0 | Not sound: Indicates a broken upstream payload or structural schema breaking change; network retries cannot fix invalid JSON syntax. | Log `PARSE_SCHEMA_MISMATCH`, save raw malformed bytes to `./traces/malformed/`, and abort run as `incomplete`. |

No failure is ever converted into a value (e.g., "0 jobs"). When a fetch fails, times out, or receives a non-200 code, the job count field is omitted or recorded strictly as `null` (`None`), accompanied by a required `error_code` string and raw HTTP status. "0 jobs" is reserved exclusively for runs where an HTTP 200 returned a structurally sound, verified empty list `[]`.

## Permission policy

* Hosts the agent may call (exact): `boards-api.greenhouse.io`, `api.lever.co` (HTTPS only, default port 443).
* Folders it may read: `./`, `./src/`, `./tests/`, `./config/`.
* Folders it may write: Canonical resolved directories `./output/` and `./traces/` only.
* Writes that require my approval: Any file creation or modification outside `./output/` or `./traces/`, any attempt to overwrite existing files in `./config/`, and any script execution targeting filesystem deletion.
* Never, under any input: apply, email, message, log in, execute shell subprocesses (`os.system`, `subprocess.Popen`), create browser sessions, or access external credentials/tokens.
* Enforcement: In code, default-deny. All network calls pass through a centralized `SecurityPolicy.validate_network_request()` validator, and all filesystem operations pass through `SecurityPolicy.validate_file_write()`. A prompt is not enforcement.

## Wrong versions my tests must catch

1. **The Silent Failure Cloaker:** Catching general `Exception` or HTTP error statuses and writing `{"jobs": [], "count": 0}` to make the run appear clean and successful instead of recording an error state.
2. **Path Traversal via Dot-Dot / Prefix Trick:** Passing a write path like `./output/../GATE.md` or `./output_evil/payload.json` that tricks simple `startswith("./output")` string matching rather than checking `Path.resolve()`.
3. **The Infinite Retry Hang:** Retrying 404 or schema parse failures infinitely or exceeding wall-clock limits because the loop lacks an explicit request/time counter check on retries.
4. **The False Zero Invariant (Empty Board Illusion):** An ATS endpoint changing its root key (e.g., from `jobs` to `postings`) resulting in `data.get("jobs", [])` returning empty, which reports "0 new jobs" cleanly when the raw response actually contained 50 active listings.
5. **Permissive Symlink Escalation:** Attempting to write into a symlinked path inside `./output/` that points to an unauthorized parent directory (e.g., `./output/symlink_root` pointing to `/`).
