# Sampling report (Chapter 1)

- Date (UTC): 2026-10-31, run `20261031T191349Z`
- Model: `claude-sonnet-5-5` (default (JUDGE_MODEL not set)); model reported by backend: `claude-sonnet-5-5`
- Prompts: `prompts/system_v1.txt` (system), `prompts/judge_v1.txt` (user)
- Calls: 20 (5 postings x 4), each a fresh, stateless call with no retry. All logged to `evidence/claude_calls.jsonl` (tag `sampling_dev_20261031T191349Z_call<k>`).
- Invalid outputs: 0 of 20
- Raw results: `evidence/runs/20261031T191349Z_sampling_dev.json`
- Postings: the 2 `clause1_pass` dev rows (8043974, 8221248) plus 3 more dev rows sampled with seed 7375 from the other 8 dev rows (id-sorted). Dev split only.
- Claude verdicts are JUDGMENT (model output, not fact). Rule verdicts are RECORD.

## Verdicts per posting per call

| posting_id | title | group | my_label | rule (RECORD) | call 1 | call 2 | call 3 | call 4 | distinct verdicts | agree with my_label |
|---|---|---|---|---|---|---|---|---|---|---|
| 8043974 | Senior Machine Learning Engineer | clause1_pass | not_relevant | not_relevant | not_relevant | not_relevant | not_relevant | not_relevant | 1 (not_relevant) | 4/4 |
| 8221248 | Senior Oracle Security and AI Engineer | clause1_pass | not_relevant | not_relevant | not_relevant | not_relevant | not_relevant | not_relevant | 1 (not_relevant) | 4/4 |
| 7572075 | Forward Deployed Engineer (FDE) | other | not_relevant | not_relevant | not_relevant | not_relevant | not_relevant | not_relevant | 1 (not_relevant) | 4/4 |
| 8158617 | Senior Customer Engineer, Digital Native Business, Indonesia  | other | not_relevant | not_relevant | not_relevant | not_relevant | not_relevant | not_relevant | 1 (not_relevant) | 4/4 |
| 8223736 | Senior Customer Engineer, Named - Vancouver, BC  | other | not_relevant | not_relevant | not_relevant | not_relevant | not_relevant | not_relevant | 1 (not_relevant) | 4/4 |

## What this can and cannot show

- Identical verdicts across repeats show repeatability, not correctness. A judge can be consistently wrong.
- 4 samples per posting cannot estimate a rate. They can show that verdicts vary on a posting, but a posting that gave the same verdict 4 times may still flip on a later call.
- Agreement is measured against one person's labels (Meena's, under LABELING.md), not against ground truth.
- All 10 dev labels are `not_relevant`, so this sample only measures agreement on postings labeled negative.

## My conclusion

Across 4 fresh calls on each of 5 dev postings, the Claude judge returned not_relevant all 20 times, matching my hand label every time, and the validator rejected 0 of 20 outputs. That shows the verdict repeated on these five postings; it does not show the judge is correct, and 4 samples per posting are too few to estimate how often it would vary. All five were postings I labeled not_relevant, so the judge was never tested on a posting that should come back relevant. Saying anything about accuracy would need postings I would label relevant, and this board had none for a Boston-based early-career persona.
