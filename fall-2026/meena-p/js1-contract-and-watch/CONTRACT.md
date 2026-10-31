# CONTRACT — Job-Search Agent 1

Written by Meena on 2026-10-31, before any code was generated. Placeholders for fields, rule keywords, wrong version 3 and the failure sentence were resolved before any code (94f5ede). The board token (cloudflare) and persona city (Boston) were filled in after the first code commit (9c8c20a, after d138c84); neither changed a rule, since the code already used cloudflare and the city was read from resume.personal.location.

## In
- Board: Greenhouse board token `cloudflare`, fetched from host `boards-api.greenhouse.io` (the only host on the allow-list).
- Résumé: one fictional persona JSON at `resume/persona.json`, copied unmodified from the-reallocation-engine `search/examples/priya-nair/resume.example.json`. It must contain `personal.location` and `skills`. If either is missing, the agent refuses to run. The persona file has no target-title field, so the target title keywords are fixed in this contract (rule clause 1), taken from the persona's profile.yml `target_role` ("AI Engineer / ML Engineer", "Data Engineer").
- State: `state/seen_ids.json` from the previous run (absent on the baseline run).

## Out (per new posting)
- `posting_id`, `rule_verdict` (relevant | not_relevant), `rule_justification`, `claude_verdict`, `claude_justification`.
- Every justification names at least one résumé field and at least one posting field by exact key path (e.g. `resume.personal.location`, `resume.skills`, `posting.title`, `posting.location.name`), and every named field exists in the inputs.
- The rule verdict is labeled RECORD. The Claude verdict is labeled JUDGMENT (model output, not fact).

## Refuses
- Fetching any host not on the allow-list.
- Running on a résumé that is not the fictional persona (refuses any email not ending in @example.com and any phone not using 555).
- Printing or committing a real résumé.
- Presenting a Claude verdict as fact, or emitting a Claude verdict that fails the validator.
- Applying, emailing, messaging, or logging in anywhere.

## The rule (a TA can apply this by hand)
A posting is RELEVANT if and only if all three hold:
1. `posting.title` contains, case-insensitive, at least one of: "AI Engineer", "ML Engineer", "Machine Learning", "Data Engineer".
2. `posting.location.name` contains "Boston" (the city in `resume.personal.location`) or the word "Remote".
3. `posting.title` does not contain Senior, Sr., Staff, Principal, Lead, Director, Head, or Manager.

Otherwise NOT RELEVANT. The justification names which clause failed, or all three that passed. Clause 1 cites `posting.title`; clause 2 cites `posting.location.name` and `resume.personal.location`; clause 3 cites `posting.title`.

## Wrong versions my tests must catch
1. Misaligned labels: verdicts paired with the wrong posting (e.g. an off-by-one zip). Caught by a test that checks every justification quotes the title belonging to its own `posting_id`.
2. Empty or fake citation: a justification that names no field, or names a field that does not exist in the résumé or posting. Caught by a validator test.
3. "New" computed by posting title instead of `id`. Caught by a test where two postings share a title but have different ids.

## What a failure looks like
2026-10-31: Failure is any run that reports a posting id already in the previous state as new, or any verdict whose justification cites a field that does not exist in its inputs.