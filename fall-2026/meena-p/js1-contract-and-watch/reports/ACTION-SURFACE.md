# Action surface: three ways to judge posting 8335469 against CONTRACT.md

Date: 2026-10-31. Posting 8335469 is "Territory Account Executive, Saskatchewan / Manitoba", `posting.location.name` "Remote", from the live response `evidence/raw/20261031T182100Z_live.json`.

| # | Surface | Evidence |
|---|---|---|
| 1 | **Chat paste**: Meena, by hand in claude.ai | `evidence/surface_chat_prompt.txt`, `evidence/surface_chat_2026-10-31.txt` |
| 2 | **File read**: `claude -p` with a read-only tool, run by `scripts/surface_file_read.py` | `evidence/surface_file_posting.json`, `evidence/surface_file_prompt.txt`, `evidence/surface_file_output.json` |
| 3 | **Agent**: the full pipeline in `agent/run.py` | `evidence/runs/20261031T182105Z_live-vs-SEEDED-baseline_verdicts.json`, `evidence/claude_calls.jsonl` |

After the three fixes below, the SEEDED two-run was re-run from the saved files (no live fetch) into `evidence/runs/post-fix/`, with its own SEEDED state file. Run 2 again reported exactly 8332361, 8335069, 8335468, 8335469 and 8338018 as new, and its verdicts on 8335469 are unchanged (rule and Claude both `not_relevant`). The agent verdicts in the tables below are the ones it produced on 2026-10-31 at 18:39Z (`--rejudge` of run 2), before the fixes; the post-fix re-run did not change them. The agent was never run against the live board for this report, since a live run would fetch the board again and overwrite `state/seen_ids.json`.

## 1. Chat paste

The prompt contains the contract's rule text, `resume.personal.location = "Boston, MA"`, and three posting fields typed in by hand: `posting.id`, `posting.title`, `posting.location.name`. The response file records: `claude.ai fresh chat, 2026-10-31, 3:43 PM EDT, model: not recorded`. The model used is **not recorded**.

| | |
|---|---|
| **Can read** | The pasted text. Anything else claude.ai had enabled in that chat (search, connectors, memory) is not recorded in the evidence files. |
| **Can write** | Nothing on this machine. The conversation is stored in the claude.ai account. |
| **Network** | The browser sends the pasted text to claude.ai. |
| **Authority / credentials** | Meena's claude.ai login. No repo, filesystem or API key. |
| **What could go wrong** | (a) **Transcription:** the posting fields are copied by hand, and nothing checks them against the raw response. (b) **No provenance:** the model and time were not filled in (the placeholders above), so the result cannot be tied to a model. (c) **Fails the contract:** the justification cites only `posting.title`. Run through `agent/validate.py` it fails with `['no resume field cited']`; CONTRACT.md requires a résumé field too. (d) **No checks or log:** no validator or retry runs, and the only record is the hand-saved text file. (e) **Less to see:** only 3 posting fields are visible, so the model cannot see `posting.content`. |

## 2. File read

`scripts/surface_file_read.py` saved the posting unmodified (the full Greenhouse object) to `evidence/surface_file_posting.json`. It then ran `claude -p` in a fresh temp directory containing only a copy of that file; `temp_dir_listing` and matching sha256 values are recorded in the output. Settings:

- **Tools:** `--tools Read --allowedTools Read --permission-mode dontAsk --restricted --strict-mcp-config --setting-sources "" --no-session-persistence`.
- **System prompt:** `prompts/system_v1.txt`.
- **User prompt:** `evidence/surface_file_prompt.txt`, the chat prompt with only the three pasted posting lines replaced by a pointer to the file (`diff`: lines 14-16 become one line).
- **Model:** `claude-sonnet-5-5` was requested (default, `JUDGE_MODEL` not set) and reported.
- **What it did:** 2 turns; 1 tool call, `Read` of the temp copy; `permission_denials: []`.

| | |
|---|---|
| **Can read** | Files via the `Read` tool. Its working directory held only the posting copy. Whether `dontAsk` blocks a `Read` of an absolute path outside that directory was **not tested here**. |
| **Can write** | Nothing: no Write, Edit, Bash or other code-running tool was available. The calling script, not the model, wrote the evidence files. |
| **Network** | The `claude` CLI sends the prompt, the file contents it reads and its replies to Anthropic. The model had no WebFetch, WebSearch or MCP tools. |
| **Authority / credentials** | The Claude Code login on this machine (`ANTHROPIC_API_KEY` is not set). |
| **What could go wrong** | (a) **Injection:** `posting.content` is employer-written HTML, and the model reads it in full. A prompt injection there can at most request more `Read` calls, but if the working directory were the repo instead of a temp directory, those reads could reach `labels/postings_20.csv` (including held-out labels), `evidence/claude_calls.jsonl` and `resume/persona.json`. (b) **Unchecked output:** the output is free text, not the JSON contract, so no validator ran in the loop; the check below was run afterwards. (c) **Possible guessing:** a model could answer without reading the file. Here the transcript shows the `Read` call. |

## 3. Agent (`agent/run.py`)

| | |
|---|---|
| **Can read** | `resume/persona.json`, `state/seen_ids.json`, `prompts/*`, saved raw responses (`--from-file`, `--rejudge`). |
| **Can write** | `evidence/raw/*` (raw responses), `evidence/runs/*` (run and verdict files), `state/seen_ids.json`, `evidence/claude_calls.jsonl`. |
| **Network** | HTTPS GET to `boards-api.greenhouse.io` (the only allow-listed host). Claude calls through `claude -p` with no tools, or through the Anthropic API if `ANTHROPIC_API_KEY` is set. Every Claude call sends the full persona and the full posting. |
| **Authority / credentials** | None for Greenhouse (public board API). The Claude Code login on this machine, or an Anthropic API key. Filesystem write access to the repo. |
| **What could go wrong** | Concrete, from the code and from this project's history: (a) **Redirects:** the allow-list checked only the requested URL. `fetch.py` called `requests.get(url, timeout=30)`, which follows redirects by default, and did not check the final `resp.url`, so a redirect to another host would have been fetched and saved. **Found, then fixed in `9b6aa2a`** (failing test `bdd8f18`): redirects are disabled and any 3xx raises `HostNotAllowedError` before anything is saved. (b) **State written too early:** state was saved (`run.py:64`) before the judges ran (`run.py:87`). If judging failed partway, those postings were already marked seen and would not be reported as new again. **Found, then fixed in `c809e8e`** (failing test `96abd18`): `state/seen_ids.json` is written only after both judges have produced output for every new posting. (c) **Validator gap:** a nonexistent indexed path in justification text, e.g. `resume.experience.7.title`, passed both `agent/validate.py` and `agent/validator.py` (tested on 2026-10-31: both returned `[]`). The text regex stopped at the numeric segment and checked only `resume.experience`. **Found, then fixed in `baffe7f`** (failing test `6632159`): every segment, including list indexes, is resolved against the document. All 65 Claude justifications saved before the fix still pass. (d) **Evidence contamination:** the write surface includes evidence files. This happened twice. First, a test wrote a fake call line into `evidence/claude_calls.jsonl` (found and removed before the real calls; guard test added). Second, while the Gap (b) test was being written, it appended 2 `injected` lines; they were discarded with `git checkout`, and `tests/conftest.py` (`96abd18`) now redirects the log for every test. (e) **Truth not checked:** the validator checks that cited fields exist, not that what the justification says about them is true. |

## Verdicts on 8335469

| Source | Criteria applied | Verdict | Fields cited | `agent/validate.py` on the justification |
|---|---|---|---|---|
| Rule judge (RECORD), agent | CONTRACT.md rule, deterministic | not_relevant: clause 1 failed; 2, 3 passed | `posting.title`, `posting.location.name`, `resume.personal.location` | `[]` (passes) |
| 1. Chat paste (JUDGMENT) | CONTRACT.md rule (pasted) | not_relevant: "fails clause 1" | `posting.title` | `['no resume field cited']` |
| 2. File read (JUDGMENT) | CONTRACT.md rule (same text) | not_relevant: clause 1 failed; 2, 3 passed | `posting.title`, `posting.location.name`, `resume.personal.location` | `[]` (passes) |
| 3. Agent, Claude judge (JUDGMENT) | `prompts/judge_v1.txt` (LABELING.md criteria, not the contract rule) | not_relevant | `posting.content`, `posting.metadata`, `resume.experience.0.title`, `resume.skills.languages` | `[]` (passes) |

All four say `not_relevant`. Surfaces 1 and 2 apply the same rule as the rule judge, and both name clause 1 as the failing clause, matching it. Surface 2 also reports clauses 2 and 3 as passed, which matches the rule judge's result for every clause. The agent's Claude judge answers a different question (LABELING.md criteria via judge_v1), so its agreement is on the verdict only, not on the reasoning. One posting is one case: this table shows that the surfaces agree on 8335469, not that they agree in general.

## Least autonomy that suffices

The task only requires deterministic execution for fetching job payloads, tracking processed IDs in local state, and applying the baseline filtering rules; only the final ambiguous evaluation step actually requires a model judgment. 

I chose the local read-only file surface piped through our schema validator because it isolates the model's judgment to strict data inputs while programmatically enforcing our contract boundaries. 

When testing the chat surface, the model’s justification cited no résumé field at all and silently passed without anything catching the omission, whereas the file surface subjected the exact same model output to our validator and flagged schema discrepancies immediately. 

Granting extra autonomy introduces unneeded network and filesystem write access, which directly creates vulnerabilities: the three core implementation gaps Claude Code discovered—unhandled redirects, state being committed prior to validation, and fragile citation path checking—occurred precisely within the pipeline components possessing that elevated access.