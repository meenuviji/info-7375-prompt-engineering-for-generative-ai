# Prompt: justify shortlist claims

Used 2026-11-25 by Claude Code (claude-opus-5-5) to produce `shortlist/claims.csv`.
Raw answer: `notes/shortlist_draft_2026-11-25.md`.

## 1. Task as given by Meena Periasamy (verbatim)

> Take the 5 highest-scoring KEPT postings in output/filter_results_v2.csv (ties broken by id). For each, write 3 short claims a recruiter might make about why it fits the persona in FILTER.md (for example "requires Python", "is entry-level", "involves building ML models"). For each claim, quote the single sentence from that posting's description that is the best evidence, or write NO SENTENCE FOUND. Apply FILTER.md section 2's abstention rule literally: if no sentence contains the claim's key term, the claim's agent_answer is "I cannot tell"; otherwise agent_answer is "supported".

## 2. FILTER.md section 2 (verbatim, FILTER.md v1 as committed)

> - **Supported:** A sentence in the posting's own text explicitly states the claim in equivalent terms, and that exact sentence is quoted verbatim.
> - **Contradicted:** A sentence in the posting explicitly states the opposite of the claim (for example, the claim asserts remote work while the posting states on-site only).
> - **Insufficient:** No sentence in the posting directly establishes the claim, or a sentence mentions a keyword in passing without supporting the specific claim (for example, "partner with our ML team" does not support "this role builds ML models").
> - **The agent must say "I cannot tell"** when the posting has no description text, or when no quoted sentence contains the claim's key concept or requirement.

## 3. Persona (FILTER.md, verbatim)

> Jordan Lee, an entry-level / new-grad Data Engineer, Data Scientist, BI Analyst, and AI/ML Engineer looking for individual-contributor roles in the US or remote.

## 4. Operating rules added by Claude Code to make the task executable

1. Postings: KEPT rows of `output/filter_results_v2.csv`, sorted by score descending, then id ascending. If fewer than 5 are KEPT, take all of them and say so; never fill with non-KEPT postings.
2. Description text: exactly what `src/postings.py` loads (Greenhouse `content` with tags stripped; Lever `descriptionPlain`). Title, location and other fields are not evidence.
3. Each claim names one key term before any sentence is chosen. A sentence "contains" the key term when the term occurs as a whole word or phrase, case-insensitive (a hyphen and a space are treated as the same).
4. Sentence = one line of the loaded description, or one sentence within a line ending in `.`, `!` or `?`. Quotes are copied verbatim and checked by string containment against the description.
5. If several sentences contain the key term, quote the one that most directly states the claim.
6. agent_answer is only "supported" (a quoted sentence contains the key term) or "I cannot tell" (none does). The agent never outputs "contradicted" or "insufficient"; those are human labels.
7. my_label and my_reason are left blank for the human.
