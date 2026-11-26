# Score report — DRAFT

**Computed by score_report.py; interpretation to be written by me.**

## 1. Numbers and prompts that affect scoring or the shortlist

Origins: *hand-set* (a person chose it), *fitted* (code chose it from my labels) or *inherited* (from JS2 or a statistics convention). No code in this project fits a parameter, so nothing below is marked fitted.

| Item | Value | Where | Origin |
|---|---|---|---|
| Role weight (v1/v2) | 3 | `src/config.py ROLE_SCORE` | hand-set: FILTER.md v1 as first committed (7b96757), section 1.4 |
| Topic weight (v1/v2) | 1 | `src/config.py TOPIC_POINT` | hand-set: FILTER.md v1 (7b96757) |
| Topic cap (v1/v2) | 4 | `src/config.py TOPIC_CAP` | hand-set: FILTER.md v1 (7b96757) |
| Keep threshold (v1/v2) | >= 5 | `src/config.py KEEP_THRESHOLD` | hand-set: FILTER.md v1 (7b96757); chosen over the build instructions' >= 4 on 2026-11-25 |
| Close-call band (v1/v2) | scores [4, 5] | `src/config.py CLOSE_CALL_SCORES` | hand-set: FILTER.md v1 (7b96757) |
| v2 rule change | R5 = ["new grad", "university grad", "early career", "junior", "entry level"] ("associate" removed) | `src/filter.py ROLE_RULES_V2` | hand-set: chosen by me on 2026-11-25 after reading the set A audit; not fitted by code; the v2 diff was never applied to FILTER.md |
| Weights / threshold (v3) | core role 2, R5 1, topic 1, no cap, keep >= 5, close call 4 or X3/X5-only | `src/config.py V3_*` | hand-set: FILTER.md as committed in 4923b21 (header says v1) |
| US city list (v3 X3) | 16 cities | `src/location.py US_CITIES` | hand-set by Claude Code while implementing (judgment call, not in FILTER.md) |
| Sampling seed | 20261125 | `src/config.py SEED` | hand-set: JS3 build instructions (2026-11-25), not FILTER.md |
| Sample sizes | A: 30 rejected + 5 close + 5 kept (4 available); B: 30 | `src/config.py SET_*` | hand-set: JS3 build instructions (2026-11-25) |
| Wilson z | 1.96 | `audit.py Z` | inherited: statistics convention (two-sided 95% normal quantile) |
| Rule of three | 3/n | `audit.py` | inherited: statistics convention (95% upper bound when 0 events) |
| Label preview | 800 characters | `label.py PREVIEW_CHARS` | hand-set: JS3 build instructions (affects what I saw while labeling, not scoring) |
| Claim prompt | justify_claims.md (29 lines) | `prompts/justify_claims.md` | hand-written: my task text + FILTER.md section 2, with operating rules added by Claude Code |
| Data snapshot | 3 boards, 1167 postings | `data/raw/, data/SOURCES_OF_DATA.md` | inherited: JS2 run 20261110T203921572430Z (boards from JS2's config) |

## 2. Experiments on held-out set B

Set B: 30 postings labeled blind. My verdicts: y 0, n 30, ? 0 ("?" excluded from agree / false keep / false reject and counted separately).
Baseline recomputed from code matches `output/filter_results_v2.csv`: yes.

Each change alters one object only: Change 1 the keep threshold (a setting), Change 2 the filter file (v2 -> v1, whose only difference is "associate" in R5; the topic rules are identical in v1 and v2).

| Run | Configuration | Judged | Agree | Agree % | False keeps | False rejects | Filter CANNOT_TELL | "?" | Kept in set B | Kept, all 1167 |
|---|---|---|---|---|---|---|---|---|---|---|
| Baseline | filter v2, threshold 5 | 30 | 30 | 100.0% | 0 | 0 | 0 | 0 | 0 | 3 |
| Change 1 (setting) | filter v2, threshold 4 | 30 | 30 | 100.0% | 0 | 0 | 0 | 0 | 0 | 12 |
| Change 2 (filter file) | filter v1, threshold 5 | 30 | 30 | 100.0% | 0 | 0 | 0 | 0 | 0 | 4 |

### Difference from baseline (in postings; n = 30)

| Run | Δ agree | Δ false keeps | Δ false rejects | Δ kept in set B | Δ kept, all 1167 | Set B postings whose decision changed |
|---|---|---|---|---|---|---|
| Change 1 (setting) | +0 | +0 | +0 | +0 | +9 | 0 |
| Change 2 (filter file) | +0 | +0 | +0 | +0 | +1 | 0 |

### Postings whose decision changed (all 1167, for context; only set B rows are measured)

**Change 1 (setting):** 9 posting(s)

| Provider/id | Title | Baseline | This run | Score | rules_fired | In set B (my verdict) |
|---|---|---|---|---|---|---|
| greenhouse/7194969 | AI Research Engineer - Datadog AI Research (DAIR) | REJECTED | KEPT | 4 | T1;T3;T4;T5 | no |
| greenhouse/8248907 | Deal Intelligence Analyst | REJECTED | KEPT | 4 | T1;T2;T3;T5 | no |
| greenhouse/8300518 | Capacity Planning Engineer | REJECTED | KEPT | 4 | T1;T2;T3;T5 | no |
| greenhouse/8305918 | Product Cost Analyst | REJECTED | KEPT | 4 | T1;T2;T3;T5 | no |
| greenhouse/8317733 | Security Research Analyst, WAF Managed Rules | REJECTED | KEPT | 4 | T1;T2;T3;T4;T5 | no |
| greenhouse/8317751 | Customer Reliability Engineer | REJECTED | KEPT | 4 | T1;T2;T3;T5 | no |
| lever/0f7d1e01-1f74-4786-944d-910208d390fa | Software Engineer, New Grad - Query Engines | REJECTED | KEPT | 4 | R5;T3 | no |
| lever/90329118-d9b7-4b96-acdf-13377e3196ac | Software Engineer, New Grad - Query Engines | REJECTED | KEPT | 4 | R5;T3 | no |
| lever/d5f11334-3a73-4094-b7e0-d05b54e475b8 | Deployment Strategist, New Grad - Commercial | REJECTED | KEPT | 4 | R5;T3 | no |

**Change 2 (filter file):** 1 posting(s)

| Provider/id | Title | Baseline | This run | Score | rules_fired | In set B (my verdict) |
|---|---|---|---|---|---|---|
| greenhouse/8171303 | GTM Strategy/Operations Associate | REJECTED | KEPT | 6 | R5;T1;T2;T5 | no |

## Interpretation

_To be written by me._

## Interpretation

### 1. Held-Out Set B Performance and Sample Power (`n = 30`)
On the 30 blind-labeled postings in Set B, **Baseline** (`filter v2`, threshold `5`), **Change 1** (`filter v2`, threshold `4`), and **Change 2** (`filter v1`, threshold `5`) all achieved **100.0% agreement (`30/30`)**, with `0` false keeps, `0` false rejects, and `0` kept postings in Set B (`Δ agree = +0`, `0` Set B decision changes across runs). Because Set B is an unweighted random draw of 30 postings from a corpus of 1,167 where true entry-level US data/AI roles are rare (all 30 drawn postings were `n`), neither experiment moved the Set B accuracy metric—any shift of one or two postings on `n = 30` is indistinguishable from sampling noise.

### 2. What Moved Across the Full Corpus (1,167 Postings)
Inspecting the full-corpus decision diffs shows why the two changes were separated and how each behaves outside Set B:
- **Change 1 (Lowering keep threshold from `5` to `4`):** Did not change any Set B decision (`0/30`), though across all 1,167 postings it admitted **9 additional postings** (`Kept, all 1167` rose from `3` to `12`). Every one of those 9 newly kept rows is a **false positive** against Jordan Lee's persona: six scored `4` purely from hitting the topic cap (`T1`–`T5`) with zero role-title match (`AI Research Engineer - DAIR`, `Deal Intelligence Analyst`, `Capacity Planning Engineer`, `Product Cost Analyst`, `Security Research Analyst`, `Customer Reliability Engineer`), and three scored `4` from `R5` (`New Grad`) plus `T3` (`Software Engineer, New Grad - Query Engines` and `Deployment Strategist, New Grad - Commercial`). Keeping the threshold at `5` prevents topic-only or generic new-grad roles from passing without a core role match.
- **Change 2 (Reverting `FILTER.md` from `v2` back to `v1`, restoring `"associate"` in `R5`):** Did not change any Set B decision (`0/30`), and across all 1,167 postings it moved only **1 posting** (`Kept, all 1167` rose from `3` to `4`): `greenhouse/8171303` (`GTM Strategy/Operations Associate`, score `6` via `R5;T1;T2;T5`), which I already labeled `n` in Set A. Removing `"associate"` from `R5` in `v2` eliminates that exact false positive without losing any valid matches.

### 3. Why Persistence Is Configuration, Not Learning
Behavior that persists across sessions is not proof that anything was trained. In this agent, every behavior change came from a file (`FILTER.md`), a setting (the threshold), or a prompt (`prompts/justify_claims.md`). No model weights changed.
