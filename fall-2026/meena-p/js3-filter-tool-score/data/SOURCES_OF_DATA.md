# Sources of data for JS3

Copied on 2026-11-25 from JS2's saved raw responses, byte for byte (no edits).
JS2 was only read; nothing in `../js2-loop-tools-diff/` was changed.

All three files come from the most recent JS2 run, run id `20261110T203921572430Z`
(2026-11-10 20:39:21 UTC, the clean run that exited 0). The earlier run
`20261110T203826744076Z` has the same boards; its cloudflare and palantir bodies are
byte-identical to these, and its datadog body differs by 44 bytes with the same set of ids.
`output/raw/<run id>/` in JS2 holds identical copies of the `output/real_run/<run id>/raw/` files.

| File in data/raw/ | Source (relative to this JS3 folder) | Board | Provider | JS2 timestamp (UTC) | Bytes | sha256 | Postings |
|---|---|---|---|---|---|---|---|
| `greenhouse_cloudflare_attempt1.body` | `../js2-loop-tools-diff/output/real_run/20261110T203921572430Z/raw/greenhouse_cloudflare_attempt1.body` | cloudflare | Greenhouse | 20261110T203921572430Z | 8303393 | `9a43d1647f15b57c4ad8a522f04fe9e504c369c4e2f0b0bae62ba3bdea5b585d` | 468 |
| `greenhouse_datadog_attempt1.body` | `../js2-loop-tools-diff/output/real_run/20261110T203921572430Z/raw/greenhouse_datadog_attempt1.body` | datadog | Greenhouse | 20261110T203921572430Z | 4918938 | `1d3803ae16c8a672382639a6fd658a6f543680fbf540d9b563b21e179e914d95` | 395 |
| `lever_palantir_attempt1.body` | `../js2-loop-tools-diff/output/real_run/20261110T203921572430Z/raw/lever_palantir_attempt1.body` | palantir | Lever | 20261110T203921572430Z | 5927140 | `8bf628ff1e2bc32a98c9e2c344f75f267e3de5b41daf375d3aec8f25e4dceb84` | 304 |

Request URLs JS2 used (from its trace):
- `https://boards-api.greenhouse.io/v1/boards/cloudflare/jobs?content=true`
- `https://boards-api.greenhouse.io/v1/boards/datadog/jobs?content=true`
- `https://api.lever.co/v0/postings/palantir?mode=json`

Description fields checked before any code: Greenhouse `content` is non-empty in 468/468 and
395/395 postings; Lever `descriptionPlain` is non-empty in 304/304 postings.
No fresh fetch was needed.
