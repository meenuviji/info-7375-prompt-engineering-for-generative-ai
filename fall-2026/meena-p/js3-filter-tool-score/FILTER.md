# FILTER.md — Job-Search Agent 3

Version: v1 — 2026-11-25
Written by Meena Periasamy before any JS3 code (refined from an initial structure drafted with Claude).

Persona (fictional, for GitHub): Jordan Lee, an entry-level / new-grad Data Engineer, Data Scientist, BI Analyst, and AI/ML Engineer looking for individual-contributor roles in the US or remote.

## 1. The filter

A posting is **kept** when no exclusion rule matches its title and its score meets or exceeds the threshold. A posting whose title matches at least one role rule (or entry-level signal) but lacks description text is marked **CANNOT_TELL** — never silently rejected.

**Matching method for every rule:** whole word or whole phrase, case-insensitive, using word boundaries (`\b...\b`). Substring matching is prohibited because it causes false positives such as `"AI"` matching `"Maintenance"` or `"ML"` matching `"HTML"` (Wrong Version W1).

### 1.1 Role rules (title only)
| ID | Words or phrases | Reason |
|---|---|---|
| R1 | data engineer, data engineering, analytics engineer | Core data-pipeline and warehousing roles matching my engineering focus. |
| R2 | data scientist, data science | Core modeling, experimentation, and statistical analysis roles. |
| R3 | machine learning, ML, AI engineer, applied AI | Applied ML and AI engineering roles building production models and retrieval systems. |
| R4 | business intelligence, BI engineer, BI analyst, data analyst | Analytics and BI roles focused on SQL, metrics, and decision support. |
| R5 | new grad, university grad, early career, associate, junior, entry level | Entry-level role titles suitable for a December 2026 graduate. |

### 1.2 Topic rules (description only; each rule counts at most once)
| ID | Words or phrases | Reason |
|---|---|---|
| T1 | python, pandas, pyspark | Primary programming ecosystem required for data and ML workflows. |
| T2 | sql, snowflake, bigquery, postgresql, redshift | Core relational querying and cloud data warehouse stack. |
| T3 | pipeline, pipelines, ETL, ELT, airflow, dbt, kafka | Signals genuine data-engineering and orchestration responsibilities. |
| T4 | machine learning, deep learning, pytorch, tensorflow, scikit-learn, NLP, RAG | Signals hands-on model training, evaluation, or retrieval engineering. |
| T5 | time series, forecasting, tableau, power bi, dashboard, dashboards | Matches my forecasting and BI visualization specialization. |

### 1.3 Exclusion rules (title only)
| ID | Words | Reason |
|---|---|---|
| X1 | senior, sr, staff, principal, distinguished, director, head, manager, vp, vice president | Persona targets entry-level / early-career IC roles; management and senior tracks are out of scope. Applied strictly to the title because descriptions frequently say "collaborate with senior engineers" (Wrong Version W4). |
| X2 | intern, internship, co-op | Persona is seeking full-time post-graduation roles rather than student internships. |

### 1.4 Score and threshold
- **Base role score:** `3` if at least one role rule (`R1`–`R5`) matches the title; `0` otherwise.
- **Topic score:** `+1` for each distinct topic rule (`T1`–`T5`) that matches the description (capped at `4` points so verbose descriptions cannot inflate rankings, Wrong Version W2).
- **Exclusions:** If any exclusion rule (`X1`–`X2`) matches the title, the posting is **REJECTED** regardless of score.
- **Keep threshold:** **Score ≥ 5** (requires a relevant title match plus at least two distinct technical topic matches in the description).
- **Close call window:** **Score 4** (one topic short of threshold) or **Score 5** (right on the threshold boundary).
- Every weight and threshold here is hand-set by Meena Periasamy; none was fitted on data (see `SCORE_REPORT.md`).

## 2. Evidence rules (for claims in the shortlist)
- **Supported:** A sentence in the posting's own text explicitly states the claim in equivalent terms, and that exact sentence is quoted verbatim.
- **Contradicted:** A sentence in the posting explicitly states the opposite of the claim (for example, the claim asserts remote work while the posting states on-site only).
- **Insufficient:** No sentence in the posting directly establishes the claim, or a sentence mentions a keyword in passing without supporting the specific claim (for example, "partner with our ML team" does not support "this role builds ML models").
- **The agent must say "I cannot tell"** when the posting has no description text, or when no quoted sentence contains the claim's key concept or requirement.

## 3. Expected sources
- **Boards and providers:** `cloudflare` and `datadog` (Greenhouse), and `palantir` (Lever), read from JS2's saved raw responses (or a single allow-listed fetch with `?content=true` if raw bodies lack descriptions).
- **Fields read:** `title`, `location`, and description (`content` with HTML tags stripped for Greenhouse; `descriptionPlain` for Lever).
- **Missing-field handling:**
  - Missing `title` → skip posting and record in skipped count.
  - Missing `description` → topic rules cannot fire; if a role rule matched the title and no exclusion fired, label **CANNOT_TELL** rather than rejecting for low score (Wrong Version W3).
  - Missing `location` → record as `"unknown"`, never inferred.

## 4. Wrong versions my tests must catch
- **W1 (Substring matching):** Matching `"AI"` inside `"Maintenance"` or `"ML"` inside `"HTML"` instead of enforcing `\b...\b` word boundaries.
- **W2 (Raw keyword frequency ranking):** Summing repeated occurrences of `"data"` or `"python"` so a 1,500-word posting outranks a concise 300-word posting with stronger role alignment.
- **W3 (Silent rejection on missing text):** Rejecting a title-matched posting when its description body is empty/null instead of returning `CANNOT_TELL`.
- **W4 (Body-level seniority exclusion):** Applying exclusion keywords like `"senior"` to the description text, causing `"work alongside senior engineers"` to reject an entry-level posting.

## 5. Change log
| Version | Date | Change | Measured on | Result | Decision |
|---|---|---|---|---|---|
| v1 | 2026-11-25 | Initial hand-authored filter before code | — | — | Baseline |
