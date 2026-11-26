# Evaluation: js3-filter MCP server (`mcp_server.py`)

**Draft by Claude Code; trust decision to be written by me.**

Evaluated 2026-11-25 as if written by a stranger, by reading `mcp_server.py` at commit
`7610235` and the modules it imports (`src/postings.py`, `src/filter_v3.py`,
`src/location.py`, `src/config.py`), plus the transcripts in `transcripts/`. Line numbers refer
to `mcp_server.py` unless another file is named. The server was not run again for this draft.

Transcripts read:
- `transcripts/mcp_20261126T011605838379Z.jsonl` (the newest) and `…011603062737Z.jsonl`: two
  sessions from Claude Code 2.1.332. Each one is `server/discover`, then `initialize`, then
  `notifications/initialized`, then `tools/list`. **Neither contains a `tools/call`.**
- `transcripts/mcp_20261126T011510667170Z.jsonl`: the `mcp_client.py` demo, the only transcript
  in which the tool was actually called.

## (a) What it declared versus what it does

### Declared (the `tools/list` reply in the newest transcript, matching lines 45–57)

| Item | Declared |
|---|---|
| serverInfo | `js3-filter` `1.0` (line 38) |
| capabilities | `{"tools": {}}` only (line 160) |
| tool | exactly one: `score_posting`, title "Score a job posting" |
| description | "Score one posting from the JS3 data snapshot (cloudflare, datadog, palantir) with the FILTER.md rules. Returns decision (KEPT/REJECTED/CANNOT_TELL), score, rules_fired and close_call. Read-only." |
| inputSchema | object; `posting_id` string, required; `additionalProperties: false` |
| outputSchema | none |

### Actual (code)

| Declared | What the code does | Where |
|---|---|---|
| one tool | `TOOLS` has one entry; any other name is a JSON-RPC -32602 error | 58, 131–132 |
| input `{"posting_id": string}` | requires **exactly** that key and a string, 1–200 characters; anything else is -32602 | 133–137 |
| "Score one posting from the JS3 data snapshot" | loads every posting under the fixed `data/raw/` once, on the first call, and looks the id up in a dict | 94–100; `src/postings.py:132` |
| "with the FILTER.md rules" | scores with rule set **v3** (`src/filter_v3.py`), and first refuses if FILTER.md's sha256 differs from the one v3 was built from | 108–113, 120 |
| returns decision, score, rules_fired, close_call | returns those four **plus** `posting_id`, `provider`, `board`, `title`, `rule_set`, `filter_md_version`, `filter_md_sha256`, as JSON text and as `structuredContent` | 121–124, 142–143 |
| "Read-only" | reads `FILTER.md` on every call (102–105) and `data/raw/` once. **It writes**: every line received and sent goes to a new transcript file | 65–80, 194–205 |
| (protocol) | answers `initialize`, `tools/list`, `tools/call`; every other request gets -32601; every notification is ignored | 145–170 |

What the newest transcript shows: Claude Code asked for protocol `2025-11-25`. The server
doesn't list that version (line 39), so it answered `2025-06-18` (lines 158–159), and the
client carried on with `tools/list`. The client's `server/discover` probe got -32601
(line 166).

## (b) What a compatible client is not entitled to

| A client cannot… | Enforced by | Strength |
|---|---|---|
| read another file through the tool | `posting_id` is only a dict key (114); the data folder and FILTER.md paths are fixed in code (89; `src/postings.py:132`); no argument is ever joined into a path. Demo: `../../etc/passwd` → "unknown posting_id" (transcript `…011510…`) | by construction |
| pass extra or differently typed arguments | exact key set and type check (134–135); length limit (136–137) | code check |
| call any other tool or method | 131–132 (-32602), 166 (-32601) | code check |
| make the server use the network | `mcp_server.py` and the `src/` modules it imports import no network module (no `socket`, `urllib`, `requests`, `http`) | **by absence only** |
| make the server write anything except its transcript | the only `open` for writing is the transcript, mode `"x"` (71) | **by absence only** |
| choose where the transcript goes | `--transcript-dir` is a command-line argument set by whoever starts the process (210), not something a client can send | code check |
| get scores under rules FILTER.md no longer describes | sha256 check (110–113) | code check, FILTER.md only |

Where **nothing** enforces a limit:
- **No sandbox.** The process runs with the full file and network permissions of whoever starts
  it. "No network" and "no other writes" hold only because the code doesn't do those things.
  Nothing at the operating-system level stops it, and nothing would catch a future edit that
  added a network call.
- **Transcript size.** Every received line is logged *before* it is validated (197), and there
  is no limit on line length or number of lines. A client can make the server write arbitrarily
  large files and hold arbitrarily long lines in memory.
- **What the transcript holds.** It stores the client's full `initialize` payload, including
  `clientInfo`. Two such files, `…011510…` and `…011603…`, were committed to git in `7610235`.
- **Echoed input.** Error text repeats the client's `posting_id` back (116).

## (c) Gaps between declared and actual behaviour

1. **"Read-only" isn't quite true.** The server writes a transcript of every message, the
   description doesn't mention it, and its size is unbounded (see (b)).
2. **"with the FILTER.md rules" claims more than the code can.** v3 includes choices FILTER.md
   doesn't state:
   - the US city list and the "Available Location(s)" fallback (`src/location.py`)
   - when CANNOT_TELL applies
   - using the X5 regex literally
   - the "word right before `pipeline`" reading of T3

   The result reports `rule_set: "v3"` and the FILTER.md hash, but the tool description doesn't.
3. **The output is larger than declared, with no schema.** The description names 4 fields and
   the code returns 11. There's no `outputSchema`, so a client can't validate
   `structuredContent`.
4. **The drift guard covers FILTER.md only.** Edits to `src/filter_v3.py`, `src/location.py` or
   `src/config.py`, or to the files in `data/raw/`, change scores without the guard noticing.
   `data/SOURCES_OF_DATA.md` records the data hashes, but nothing checks them.
5. **The input schema is looser than the code.** The schema puts no length limit on
   `posting_id`; the code rejects ids over 200 characters (136–137).
6. **Protocol coverage is minimal.** `ping` gets -32601 even though the MCP lifecycle expects
   receivers to answer it. Calls made before `initialize` are accepted, because the lifecycle
   isn't enforced. The newest version the server negotiates is `2025-06-18`.
7. **What the transcripts don't show.** The real client sessions contain no tool call. The only
   evidence that scoring works through MCP is my own demo client and `tests/test_mcp.py`.

## Trust decision

_To be written by me._
