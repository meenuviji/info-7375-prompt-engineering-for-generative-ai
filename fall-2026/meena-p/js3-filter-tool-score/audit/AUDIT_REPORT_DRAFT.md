# Set A audit — DRAFT

**Computed by audit.py; interpretation to be written by me.**

Inputs: `labels/set_A_labels.csv` (39 rows), `labels/set_A_key.csv`, `output/filter_results.csv` (filter FILTER.md v1, keep threshold 5).
Agree = filter KEPT & y, or filter REJECTED & n. Filter error = filter REJECTED & y, or filter KEPT & n. "?" answers are counted separately and are in neither.

## 1. Agreement by sampling group

### Random rejects (n = 30; filter decisions: REJECTED 30)

| Outcome | Count |
|---|---|
| Agree with filter | 30 |
| Filter error | 0 |
| My "?" (cannot tell) | 0 |

### Close calls (n = 5; filter decisions: REJECTED 5)

| Outcome | Count |
|---|---|
| Agree with filter | 5 |
| Filter error | 0 |
| My "?" (cannot tell) | 0 |

### Kept (n = 4; filter decisions: KEPT 4)

| Outcome | Count |
|---|---|
| Agree with filter | 1 |
| Filter error | 3 |
| My "?" (cannot tell) | 0 |

## 2. Random rejects: error proportion

- Sample: 30 postings drawn at random (seed 20261125) from the 1163 postings the filter REJECTED. "?" answers: 0 (excluded from the denominator).
- **In this sample of 30:** I labeled 0 of 30 as relevant (y), so the filter rejected 0 relevant postings in this sample (0/30 = 0.000).
- **Estimate for all 1163 rejects:** error proportion 0.000, 95% Wilson interval [0.000, 0.114] (about 0 to 132 of 1163 rejects, if the sample is representative).
- Errors are 0, so the rule-of-three 95% upper bound is 3/30 = 0.100.
- This is an estimate for the filter's rejects in this data snapshot, from one labeler; it is not a measured rate for all postings.

## 3. Postings where the filter and I disagree (filter errors)

| Group | Filter | Score | My verdict | Title | rules_fired | my_reason |
|---|---|---|---|---|---|---|
| random_kept | KEPT | 6 | n | GTM Strategy/Operations Associate | R5;T1;T2;T5 | (none) |
| random_kept | KEPT | 7 | n | Data Scientist | R2;T1;T2;T3;T4;T5 | (none) |
| random_kept | KEPT | 6 | n | Data Analyst | R4;T1;T2;T3 | (none) |

"?" answers and filter CANNOT_TELL rows (listed separately): 0

## 4. Candidate false friends

Every rule that fired on a set A posting I marked n or ?, with the matched word and the sentence it matched in (title rules show the title). Candidates only: which of these fired for a reason unrelated to the persona is for me to judge.

| Posting (group, filter) | My verdict | Rule | Field | Matched word | Sentence |
|---|---|---|---|---|---|
| Senior Majors Account Executive - Dallas (random_rejected, REJECTED) | n | T3 | description | `pipeline` | As a Senior Majors Account Executive, you will demonstrate the highest level of sales proficiency, ensuring highly accurate forecasting, strategic pipeline management, and consistently exceeding attainment targets. |
| Senior Majors Account Executive - Dallas (random_rejected, REJECTED) | n | T5 | description | `forecasting` | As a Senior Majors Account Executive, you will demonstrate the highest level of sales proficiency, ensuring highly accurate forecasting, strategic pipeline management, and consistently exceeding attainment targets. |
| Senior Majors Account Executive - Dallas (random_rejected, REJECTED) | n | X1 | title | `Senior` | Senior Majors Account Executive - Dallas |
| AI Research Scientist - Datadog AI Research (DAIR) (random_rejected, REJECTED) | n | T3 | description | `pipelines` | Experience writing production data pipelines and applications |
| AI Research Scientist - Datadog AI Research (DAIR) (random_rejected, REJECTED) | n | T4 | description | `machine learning` | Conduct research in generative AI and machine learning, building specialized foundation models and trained agents for observability |
| AI Research Scientist - Datadog AI Research (DAIR) (random_rejected, REJECTED) | n | T5 | description | `time series` | Building on our track record of AI-powered solutions (e.g., Bits AI, Bits Evolve, and our time series foundation model), Datadog AI Research tackles high-risk, high-reward problems grounded in real-world challenges in cloud observability and security. |
| AI Research Scientist - Datadog AI Research (DAIR) (random_rejected, REJECTED) | n | T3 | description | `pipelines` | Experience writing production data pipelines and applications |
| AI Research Scientist - Datadog AI Research (DAIR) (random_rejected, REJECTED) | n | T4 | description | `machine learning` | Conduct research in generative AI and machine learning, building specialized foundation models and trained agents for observability |
| AI Research Scientist - Datadog AI Research (DAIR) (random_rejected, REJECTED) | n | T5 | description | `time series` | Building on our track record of AI-powered solutions (e.g., Bits AI, Bits Evolve, and our time series foundation model), Datadog AI Research tackles high-risk, high-reward problems grounded in real-world challenges in cloud observability and security. |
| GTM Strategy/Operations Associate (random_kept, KEPT) | n | R5 | title | `Associate` | GTM Strategy/Operations Associate |
| GTM Strategy/Operations Associate (random_kept, KEPT) | n | T1 | description | `Python` | You have experience with, or an interest in learning, business intelligence and data analysis tools such as Tableau, Looker, Metabase, SQL, or Python; experience with Sales or Customer Success strategy, SaaS, or high-tech businesses is a plus |
| GTM Strategy/Operations Associate (random_kept, KEPT) | n | T2 | description | `SQL` | You have experience with, or an interest in learning, business intelligence and data analysis tools such as Tableau, Looker, Metabase, SQL, or Python; experience with Sales or Customer Success strategy, SaaS, or high-tech businesses is a plus |
| GTM Strategy/Operations Associate (random_kept, KEPT) | n | T5 | description | `dashboards` | Build dashboards and define KPIs that translate complex data into actionable insights for business leaders |
| Associate, Strategic Finance & Investor Relations (close_call, REJECTED) | n | R5 | title | `Associate` | Associate, Strategic Finance & Investor Relations |
| Associate, Strategic Finance & Investor Relations (close_call, REJECTED) | n | T5 | description | `forecasting` | Support the guidance process, including share count forecasting, sensitivity analyses, and supporting materials for leadership. |
| Software Engineer - Edge (random_rejected, REJECTED) | n | T3 | description | `ETL` | This is a team of developers creating software for the far-edge, including streaming ETL pipelines, inference platforms, and various timing critical applications. |
| Technical Escalations Engineer II (Revenue and Cost Management) - APJ (random_rejected, REJECTED) | n | T3 | description | `pipelines` | Experienced working across technical and business boundaries — equally comfortable with backend telemetry pipelines and customer-facing impact and urgency. |
| Senior Financial Systems Analyst (random_rejected, REJECTED) | n | T1 | description | `Python` | You will leverage technologies such as AI tools, SQL, Python, Tableau, and financial systems to analyze data, automate workflows, and deliver actionable insights. |
| Senior Financial Systems Analyst (random_rejected, REJECTED) | n | T2 | description | `SQL` | You will leverage technologies such as AI tools, SQL, Python, Tableau, and financial systems to analyze data, automate workflows, and deliver actionable insights. |
| Senior Financial Systems Analyst (random_rejected, REJECTED) | n | T5 | description | `Tableau` | You will leverage technologies such as AI tools, SQL, Python, Tableau, and financial systems to analyze data, automate workflows, and deliver actionable insights. |
| Senior Financial Systems Analyst (random_rejected, REJECTED) | n | X1 | title | `Senior` | Senior Financial Systems Analyst |
| Forward Deployed Software Engineer, Internship - AUS Government (random_rejected, REJECTED) | n | X2 | title | `Internship` | Forward Deployed Software Engineer, Internship - AUS Government |
| Developer Advocate - Service Management (random_rejected, REJECTED) | n | T1 | description | `Python` | You are comfortable with at least one scripting and programming languages (eg Node.js, Python, Go, bash) and are familiar with working with APIs and modern infrastructure such as IaaS cloud services and containers |
| Forward Deployed Software Engineer, New Grad - Warp Speed (random_rejected, REJECTED) | n | R5 | title | `New Grad` | Forward Deployed Software Engineer, New Grad - Warp Speed |
| Business Development Representative - Turkish Speaking (random_rejected, REJECTED) | n | T3 | description | `pipeline` | In this role, you will contribute to Cloudflare's revenue generation engine by delivering pipeline at scale to the Sales counterparts. |
| Senior Manager, Corporate Accounting (random_rejected, REJECTED) | n | X1 | title | `Senior` | Senior Manager, Corporate Accounting |
| Senior Account Executive, Digital Native (random_rejected, REJECTED) | n | T3 | description | `Pipeline` | Pipeline & Deal Management: Build and maintain a healthy, predictable sales pipeline from lead qualification to contract negotiation and closure. |
| Senior Account Executive, Digital Native (random_rejected, REJECTED) | n | X1 | title | `Senior` | Senior Account Executive, Digital Native |
| Principal Solutions Architect - SAARC (random_rejected, REJECTED) | n | T3 | description | `pipeline` | A track record of proactively contributing to pipeline and account expansion through architectural influence — not just responding to requests. |
| Principal Solutions Architect - SAARC (random_rejected, REJECTED) | n | X1 | title | `Principal` | Principal Solutions Architect - SAARC |
| Customer Experience Manager - Dutch or Swedish Speaking (random_rejected, REJECTED) | n | T5 | description | `forecasting` | Drive strong alignment with the Sales team, contributing to team forecasting, planning, and targets. |
| Customer Experience Manager - Dutch or Swedish Speaking (random_rejected, REJECTED) | n | X1 | title | `Manager` | Customer Experience Manager - Dutch or Swedish Speaking |
| Infrastructure Business Operations Associate (close_call, REJECTED) | n | R5 | title | `Associate` | Infrastructure Business Operations Associate |
| Infrastructure Business Operations Associate (close_call, REJECTED) | n | T2 | description | `SQL` | Improve recurring workflows using spreadsheets, SQL, AI tools, lightweight automation, and clear documentation; help maintain trusted data and controls. |
| Director, Enterprise Sales (random_rejected, REJECTED) | n | X1 | title | `Director` | Director, Enterprise Sales |
| Finance Business Partner, G&A (random_rejected, REJECTED) | n | T5 | description | `forecasting` | Design, automate, and implement repeatable forecasting processes leveraging AI to replace manual efforts and optimize efficiency as the business scales. |
| Software Engineer, Internship - Infrastructure (random_rejected, REJECTED) | n | X2 | title | `Internship` | Software Engineer, Internship - Infrastructure |
| Head of Enterprise Sales, Japan (random_rejected, REJECTED) | n | T3 | description | `pipeline` | This senior leader will own both the Enterprise and Public Sector strategy for their region, ensuring resources are deployed effectively to build pipeline creation, deal progression, and multi-product adoption across Datadog’s largest and most strategic accounts. |
| Head of Enterprise Sales, Japan (random_rejected, REJECTED) | n | X1 | title | `Head` | Head of Enterprise Sales, Japan |
| Data Scientist (random_kept, KEPT) | n | R2 | title | `Data Scientist` | Data Scientist |
| Data Scientist (random_kept, KEPT) | n | T1 | description | `Python` | Our stack spans multiple languages and technologies, including Python, React, and TypeScript, and continues to evolve. |
| Data Scientist (random_kept, KEPT) | n | T2 | description | `SQL` | Experience with Spark, SQL, Tableau, Google Analytics, BigQuery (or any other Big data/Cloud equivalent) etc. |
| Data Scientist (random_kept, KEPT) | n | T3 | description | `pipelines` | You will focus on building scalable, reliable AI/ML models, services and GenAI powered application backends, partnering closely with data and full-stack engineers to deliver new features and operate the pipelines and platforms behind our products. |
| Data Scientist (random_kept, KEPT) | n | T4 | description | `machine learning` | Define, implement, and train statistical, machine learning, deep learning and generative AI models. |
| Data Scientist (random_kept, KEPT) | n | T5 | description | `Tableau` | Experience with Spark, SQL, Tableau, Google Analytics, BigQuery (or any other Big data/Cloud equivalent) etc. |
| GTM Strategy & Operations Senior Associate (random_rejected, REJECTED) | n | R5 | title | `Associate` | GTM Strategy & Operations Senior Associate |
| GTM Strategy & Operations Senior Associate (random_rejected, REJECTED) | n | T2 | description | `SQL` | Data fluency: Strong understanding of GTM data (contacts, accounts, intent and enrichment signals) and the ability to define data quality standards; comfortable with SQL and working with data warehouses and BI tools to analyze usage and outcomes |
| GTM Strategy & Operations Senior Associate (random_rejected, REJECTED) | n | T3 | description | `pipeline` | Measure impact: Define and track success metrics across every tool and data product (e.g., adoption, data quality, time saved, pipeline influenced) and use the findings to make data-driven decisions to invest, consolidate, or retire |
| GTM Strategy & Operations Senior Associate (random_rejected, REJECTED) | n | X1 | title | `Senior` | GTM Strategy & Operations Senior Associate |
| Senior Staff Product Designer, Design Lab (random_rejected, REJECTED) | n | X1 | title | `Senior` | Senior Staff Product Designer, Design Lab |
| AI Research Engineer - Datadog AI Research (DAIR) (close_call, REJECTED) | n | T1 | description | `Python` | You are proficient in Python, familiar with a systems language (e.g., Rust, C++, or Go), and comfortable with modern cloud and data infrastructure |
| AI Research Engineer - Datadog AI Research (DAIR) (close_call, REJECTED) | n | T3 | description | `pipelines` | Build and operate multimodal data pipelines, training and evaluation infrastructure, benchmarks, and internal tooling |
| AI Research Engineer - Datadog AI Research (DAIR) (close_call, REJECTED) | n | T4 | description | `PyTorch` | You have practical experience implementing and operating ML training and inference systems (e.g., PyTorch or JAX), including containerization, orchestration, and GPU acceleration |
| AI Research Engineer - Datadog AI Research (DAIR) (close_call, REJECTED) | n | T5 | description | `time series` | Building on our track record of AI-powered solutions (e.g., Bits AI, Bits Evolve, and our time series foundation model), Datadog AI Research tackles high-risk, high-reward problems grounded in real-world challenges in cloud observability and security. |
| Senior Partner Marketing Manager (random_rejected, REJECTED) | n | T3 | description | `pipeline` | In this role, you will be the primary marketing driver for our channel and cloud partner ecosystem in India, working closely with the APJ partner marketing team and Channels & Alliances sales to design a prescriptive, regionally-tailored partner strategy that accelerates pipeline and revenue growth. |
| Senior Partner Marketing Manager (random_rejected, REJECTED) | n | X1 | title | `Senior` | Senior Partner Marketing Manager |
| Data Analyst (random_kept, KEPT) | n | R4 | title | `Data Analyst` | Data Analyst |
| Data Analyst (random_kept, KEPT) | n | T1 | description | `Python` | Experience with statistical analysis programming languages (Python, R etc.) |
| Data Analyst (random_kept, KEPT) | n | T2 | description | `SQL` | Expert-level proficiency in writing and optimizing complex SQL queries is mandatory, with a proven ability to performance-tune complex queries and manage analysis workflows against large, petabyte-scale datasets (Candidates will be assessed on advanced SQL skills including window functions and common table expressions (CTEs)) |
| Data Analyst (random_kept, KEPT) | n | T3 | description | `pipelines` | Take initiative to gather requirements, define, build, and maintain pipelines and metrics |
| Strategic Account Executive (SLED) (random_rejected, REJECTED) | n | T3 | description | `pipeline` | Able to demonstrate methodology to prospect and build pipeline on your own |
| Strategic Account Executive (SLED) (random_rejected, REJECTED) | n | T5 | description | `forecasting` | Ensure high forecasting accuracy and consistency |
| Software Engineer, New Grad - Query Engines (close_call, REJECTED) | n | R5 | title | `New Grad` | Software Engineer, New Grad - Query Engines |
| Software Engineer, New Grad - Query Engines (close_call, REJECTED) | n | T3 | description | `pipelines` | Our work serves many products and workloads across Foundry, including no-code pipelines, interactive analysis, and the processing that keeps the Ontology up to date. |
| Manager I, Applied Science - Frontier Agentic Models (random_rejected, REJECTED) | n | T3 | description | `pipelines` | Drive evaluation and iteration practices for AI systems: define the quality bar and guide the team in building the offline and online evaluation pipelines needed to measure quality and detect drift |
| Manager I, Applied Science - Frontier Agentic Models (random_rejected, REJECTED) | n | T4 | description | `machine learning` | A technical leader with deep expertise in one or more areas of AI or machine learning: large language models, retrieval-augmented generation (RAG), semantic search, agentic systems, deep learning, or NLP |
| Manager I, Applied Science - Frontier Agentic Models (random_rejected, REJECTED) | n | X1 | title | `Manager` | Manager I, Applied Science - Frontier Agentic Models |
| Deployment Strategist, New Grad - Commercial (close_call, REJECTED) | n | R5 | title | `New Grad` | Deployment Strategist, New Grad - Commercial |
| Deployment Strategist, New Grad - Commercial (close_call, REJECTED) | n | T3 | description | `pipeline` | Identify relevant datasets through deep engagement with customer problems and workflows, and work with Forward Deployed Engineers to integrate the data into a stable and extensible pipeline. |

Candidate matches: 69.

## Interpretation

_To be written by me._
