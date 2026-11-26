# FILTER.md — Job-Search Agent 3

Version: v3 (2026-11-25). Sections 1–3 describe v3 (code: `src/filter_v3.py`, `src/location.py`). v1 and v2 exist only in code (`src/filter.py`) and in the change log below. In use: `run_filter.py` defaults to v1 (`--version v2` or `--version v3` selects the others); the shortlist (`shortlist/claims.csv`) was built from v2 output (`output/filter_results_v2.csv`); `mcp_server.py` scores with v3.
Written by Meena Periasamy before any JS3 code. Persona: Jordan Lee — entry-level / new-grad Data Engineer, Data Scientist, BI Analyst, or AI/ML Engineer; individual contributor; US or remote.

## 1. The filter

A posting is relevant when: at least one core role rule (`R1`–`R4`) matches the title, no exclusion rule (`X1`–`X5`) matches the title, location, or description, and the total score is greater than or equal to the keep threshold (`5`).

### 1.1 Role rules (matched against the title)
| ID | Rule (exact words, how matched: whole word? case?) | Reason (one line) |
|---|---|---|
| R1 | Whole-word, case-insensitive match for `"data engineer"` or `"analytics engineer"` | Matches core data and analytics engineering individual-contributor titles. |
| R2 | Whole-word, case-insensitive match for `"data scientist"` or `"applied scientist"` | Matches core data science and applied science modeling titles. |
| R3 | Whole-word, case-insensitive match for `"ai engineer"`, `"ml engineer"`, or `"machine learning engineer"` | Matches core AI and machine learning engineering titles. |
| R4 | Whole-word, case-insensitive match for `"bi analyst"`, `"business intelligence analyst"`, `"data analyst"`, or `"product analyst"` | Matches core business intelligence and quantitative analytics titles. |
| R5 | Whole-word, case-insensitive match for `"new grad"`, `"new graduate"`, `"entry level"`, `"entry-level"`, `"junior"`, `"early career"`, or `"associate"` — **only scores if at least one of `R1`–`R4` also matches** | Rewards explicit early-career seniority signals without letting non-data `"Associate"` or `"New Grad"` roles pass on their own. |

### 1.2 Topic rules (matched against the description text)
| ID | Rule | Reason |
|---|---|---|
| T1 | Whole-word, case-insensitive match for `"python"` or `"pyspark"` | Core programming language requirement across data, analytics, and ML roles. |
| T2 | Whole-word, case-insensitive match for `"sql"`, `"bigquery"`, `"snowflake"`, `"redshift"`, or `"postgres"` | Core querying and cloud data warehouse requirement. |
| T3 | Whole-word, case-insensitive match for `"etl"`, `"elt"`, `"airflow"`, `"dbt"`, `"kafka"`, `"spark"`, or `"data pipeline"` / `"data pipelines"` (must NOT match standalone `"pipeline"` unless preceded by `"data"`, `"etl"`, `"elt"`, `"ml"`, or `"ingestion"`) | Captures real data/ML pipeline engineering while avoiding B2B `"sales pipeline"` false friends. |
| T4 | Whole-word, case-insensitive match for `"machine learning"`, `"deep learning"`, `"pytorch"`, `"tensorflow"`, `"scikit-learn"`, `"llm"`, or `"rag"` | Captures applied ML, statistical modeling, and AI engineering work. |
| T5 | Whole-word, case-insensitive match for `"tableau"`, `"power bi"`, `"looker"`, `"dashboards"`, `"a/b testing"`, `"experimentation"`, or `"time series"` / `"demand forecasting"` (must NOT match standalone `"forecasting"` in sales quota or corporate FP&A contexts) | Captures BI visualization, experimentation, and statistical forecasting while excluding sales/finance forecasting false friends. |

### 1.3 Exclusion rules
| ID | Rule (e.g. seniority words, location) | Reason |
|---|---|---|
| X1 | Title whole-word, case-insensitive match for `"senior"`, `"sr"`, `"staff"`, `"principal"`, `"lead"`, `"manager"`, `"director"`, `"head"`, `"vp"`, `"vice president"`, or `"chief"` | Excludes mid-level, senior, and people-management roles outside an entry-level IC scope. |
| X2 | Title whole-word, case-insensitive match for `"intern"`, `"internship"`, `"co-op"`, `"coop"`, or `"year at palantir"` | Excludes temporary student internships and gap-year programs. |
| X3 | Location field does NOT contain a US state/city, `"united states"`, `"usa"`, `"u.s."`, or US-eligible `"remote"` (rejects explicit non-US locations such as `"Singapore"`, `"London"`, `"Dublin"`, `"Toronto"`, `"APJ"`, `"EMEA"`, `"Central Eastern Europe"`, `"SAARC"` when US-remote is absent) | Enforces the US or US-remote geographic constraint. |
| X4 | Title whole-word, case-insensitive match for `"account executive"`, `"sales"`, `"business development"`, `"recruiter"`, `"accounting"`, `"finance"`, `"financial systems"`, `"investor relations"`, `"gtm"`, `"operations"`, `"forward deployed"`, `"deployment strategist"`, `"developer advocate"`, `"solutions architect"`, `"customer engineer"`, `"escalations"`, or `"security analyst"` | Excludes sales, recruiting, finance, GTM/bizops, and customer-facing solutions false friends. |
| X5 | Description regex match for minimum industry experience of 3+ years (e.g., `"\b([3-9]|1[0-9])\+?\s+years?\s+of\s+(industry\s+|professional\s+|relevant\s+)?experience"`), or `"phd required"` / `"doctorate required"` | Catches experienced or PhD-only research postings (such as DAIR research tracks) that omit `"Senior"` from the title. |

### 1.4 Threshold and scoring
- Score formula: `score = 2 * count(R1..R4 matched) + 1 * matched(R5) + 1 * count(T1..T5 matched)`; any match on `X1`–`X5` immediately sets decision to `REJECTED` regardless of score.
- Keep if score ≥ `5` (with no exclusion rules triggered and at least one of `R1`–`R4` matched).
- "Close call" means: a posting with no `X1`–`X5` exclusion triggered whose score is `4` (1 point below the threshold of `5`), or a posting with score ≥ `5` rejected by a single boundary rule (`X3` or `X5`).

## 2. Evidence rules (for claims in the shortlist)
- **Supported:** The posting's `title`, `location`, or `description` explicitly states the claim in plain text or an exact technical synonym (e.g., `"Bachelor's in Computer Science"` supports degree requirement; `"New York, NY"` supports US location).
- **Contradicted:** The posting text explicitly states a value that conflicts with the persona constraint or claim (e.g., `"5+ years of production data engineering experience"` contradicts entry-level eligibility; `"Dublin, Ireland"` without remote contradicts US location).
- **Insufficient:** The posting text does not mention the attribute at all (e.g., visa sponsorship, exact salary band, or remote eligibility is omitted from the posting) or a required input field (`description` or `location`) is blank/truncated.
- **The agent must say "I cannot tell" when:** A required field is missing/ambiguous (such as Cloudflare `"Hybrid"` with no city/country listed in the description, or an empty description preventing `T1`–`T5`/`X5` evaluation) or a claim requires guessing beyond the literal text.

## 3. Expected sources
- Boards and providers: `cloudflare` (Greenhouse), `datadog` (Greenhouse), and `palantir` (Lever).
- Fields the filter reads: `title`, `location`, and `description` (plain text stripped of HTML tags).
- When a field is missing:
  - Missing `title`: mark `CANNOT_TELL` (cannot evaluate `R1`–`R5`, `X1`, `X2`, `X4`).
  - Missing or ambiguous `location` (e.g., `"Hybrid"` with no country/city in `description`): mark `CANNOT_TELL` rather than guessing US eligibility.
  - Missing `description`: `T1`–`T5` and `X5` cannot fire; if `X1`–`X4` reject via `title`/`location`, mark `REJECTED`, otherwise mark `CANNOT_TELL` (`"insufficient"`), never `"rejected for no topic match"`.

## 4. Wrong versions my tests must catch
1. **Substring matching instead of whole-word boundaries:** Matching `"ai"` inside `"maintenance"` or `"email"`, `"r"` inside `"engineer"`, or `"sr"` inside `"isr"`, causing non-technical postings to trigger `R3`/`T1` falsely.
2. **Unbounded keyword frequency / length bias:** Summing raw occurrences of `"python"` or `"sql"` across a 1,500-word description so a long non-data posting outranks a concise 250-word entry-level Data Engineer posting (each rule `T1`–`T5` must contribute at most `+1` regardless of repetition).
3. **Unanchored false-friend matching on `"pipeline"`, `"forecasting"`, or `"associate"`:** Counting `"sales pipeline"` as `T3` (`pipeline`), `"revenue/quota forecasting"` as `T5` (`forecasting`), or `"GTM Strategy/Operations Associate"` as `R5` without requiring a core data/AI title (`R1`–`R4`).
4. **Silent rejection on missing description or ambiguous `"Hybrid"` location:** Treating an empty description as `0` topic points (`REJECTED`) or assuming `"Hybrid"` means US-based instead of returning `CANNOT_TELL`.

## 5. Change log
| Version | Date | Rule added / cut / rejected | Measured on | Result | Decision |
|---|---|---|---|---|---|
| v1 | 2026-11-25 | initial (R1–R5, T1–T5, X1–X5, threshold 5). Note added 2026-11-25: the v1 coded and measured on set A is the first committed FILTER.md (`7b96757`, `src/filter.py`): R1–R5, T1–T5, X1–X2 only; role 3 + topic 1 per rule, topic part capped at 4; threshold 5; close calls at score 4–5. X3–X5 first appear in v3. | Set A (39 rows) | 35/35 rejects agreed (0% FN rate, Wilson upper bound 0.114); 3/4 keeps were FP due to missing location/experience/domain exclusions and standalone R5/T3/T5 false friends | Baseline established; harden R5, T3, T5 and add X3–X5 |
| v2 | 2026-11-25 | Cut: "associate" from R5. Everything else identical to v1 (same topic rules, X1–X2, weights, cap 4, threshold 5). Code only: `src/filter.py` `ROLE_RULES_V2`; never written into sections 1–3. | Held-out set B (n = 30; 0 labeled relevant, so only false keeps are measurable) | Set B: 30/30 agree, 0 false keeps, 0 false rejects, identical to v1 (30/30); 0 set B postings changed decision. Whole snapshot: kept 4 → 3. The one change, GTM Strategy/Operations Associate, is a set A posting I labeled n. | pending my decision |
| v3 | 2026-11-25 | Sections 1–3 of this file as committed in `4923b21`. **Added:** R2 applied scientist; R3 ml engineer, machine learning engineer; R4 business intelligence analyst, product analyst; R5 new graduate, entry-level, and R5 scores only with an R1–R4 match; T2 postgres; T3 spark, data pipeline(s), and pipeline(s) only after data/etl/elt/ml/ingestion; T4 llm; T5 looker, a/b testing, experimentation, demand forecasting; X1 lead, chief; X2 coop, year at palantir; X3 (non-US location); X4 (function titles); X5 (3+ years of experience regex, or PhD/doctorate required); CANNOT_TELL for a missing title or ambiguous location. **Cut:** R1 data engineering; R2 data science; R3 machine learning, ML, applied AI; R4 business intelligence, BI engineer; R5 university grad; T1 pandas; T2 postgresql; T3 standalone pipeline(s); T4 NLP; T5 standalone forecasting, dashboard (singular); X1 distinguished; the topic cap of 4. **Changed:** role weight 3 → 2 per R1–R4 rule, plus 1 for R5; close call redefined. **Kept:** threshold 5; "associate" stays in R5 (gated), so v2's cut was not carried over. Code interpretations not stated above: US city list and "Available Location(s)" fallback for X3, X5 regex used literally, CANNOT_TELL only when the missing field could change the outcome to KEPT. | Held-out set B (n = 30; 0 relevant, so false keeps only). Also set A (39), which is **not held-out** for v3, because these rules were written after reading the set A audit. | Set B: 30/30 agree, 0 false keeps, 0 false rejects; 0 set B postings changed decision vs v2. Set A (not held-out): 38/39 agree, 0 false keeps, 1 false reject (Data Engineer - Talent Acquisition Operations, rejected by X4 "operations"; I labeled it y). Compared with v2 on set A: false keeps 2 → 0, false rejects 0 → 1. Whole snapshot: kept 3 → 0. | pending my decision |
| v2 + threshold 4 (experiment) | 2026-11-25 | Setting change only: keep threshold 5 → 4 on v2, with no rule added or cut (close-call band unchanged). Never adopted in code; run by `score_report.py` through `keep_threshold`. | Held-out set B (n = 30; 0 labeled relevant, so only false keeps are measurable), against the v2 baseline at threshold 5 | Set B: 30/30 agree, 0 false keeps, 0 false rejects, identical to the baseline (30/30); 0 set B postings changed decision. Whole snapshot: kept 3 → 12. The 9 added are six score-4 postings with no R1–R4 title (topics only), the two Palantir "Software Engineer, New Grad - Query Engines" postings and "Deployment Strategist, New Grad - Commercial". None is in set B. See `SCORE_REPORT.md`. | pending my decision |