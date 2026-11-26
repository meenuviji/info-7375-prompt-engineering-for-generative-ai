# Shortlist Audit & Claim Verification — Job-Search Agent 3

Written by Meena Periasamy.  
Inputs: `shortlist/claims.csv`, `FILTER.md` (v1).

## 1. Shortlisted Postings and Labeled Claims

### 1. [Posting Title 1 (Posting ID)]
* **[C1]** Claim: `[claim text]` — Agent: `[agent_answer]` | Mine: `[my_label]`
* **[C2]** Claim: `[claim text]` — Agent: `[agent_answer]` | Mine: `[my_label]`
* **[C3]** Claim: `[claim text]` — Agent: `[agent_answer]` | Mine: `[my_label]`

### 2. [Posting Title 2 (Posting ID)]
* **[C4]** Claim: `[claim text]` — Agent: `[agent_answer]` | Mine: `[my_label]`
* **[C5]** Claim: `[claim text]` — Agent: `[agent_answer]` | Mine: `[my_label]`
* **[C6]** Claim: `[claim text]` — Agent: `[agent_answer]` | Mine: `[my_label]`

### 3. [Posting Title 3 (Posting ID)]
* **[C7]** Claim: `[claim text]` — Agent: `[agent_answer]` | Mine: `[my_label]`
* **[C8]** Claim: `[claim text]` — Agent: `[agent_answer]` | Mine: `[my_label]`
* **[C9]** Claim: `[claim text]` — Agent: `[agent_answer]` | Mine: `[my_label]`

### 4. [Posting Title 4 (Posting ID)]
* **[C10]** Claim: `[claim text]` — Agent: `[agent_answer]` | Mine: `[my_label]`
* **[C11]** Claim: `[claim text]` — Agent: `[agent_answer]` | Mine: `[my_label]`
* **[C12]** Claim: `[claim text]` — Agent: `[agent_answer]` | Mine: `[my_label]`

### 5. [Posting Title 5 (Posting ID)]
* **[C13]** Claim: `[claim text]` — Agent: `[agent_answer]` | Mine: `[my_label]`
* **[C14]** Claim: `[claim text]` — Agent: `[agent_answer]` | Mine: `[my_label]`
* **[C15]** Claim: `[claim text]` — Agent: `[agent_answer]` | Mine: `[my_label]`

---

## 2. Relevance Is Not Entailment

* **Claim:** `[claim_id]` — `[claim text]` (`[Posting Title]`)
* **My label:** `[insufficient / contradicted]`
* **Quoted sentence from posting:**
  > "[Exact sentence from claims.csv / posting text]"
* **Why relevance does not entail the claim:** The posting triggered my filter rules because the keyword `[matched keyword]` appeared in the text, making the job relevant at the document level. However, keyword presence only proves topical overlap—not that the specific claim holds for this role. In the quoted sentence, `[explain the gap: e.g., the term appears in a preferred/nice-to-have bullet rather than a hard requirement, describes an adjacent team rather than the candidate's own responsibilities, or states an experience/location condition that contradicts entry-level US criteria]`.

---

## 3. Abstention Rule (from `FILTER.md` §2)

> **The agent must say "I cannot tell" when:** A required field is missing/ambiguous (such as Cloudflare `"Hybrid"` with no city/country listed in the description, or an empty description preventing `T1`–`T5`/`X5` evaluation) or a claim requires guessing beyond the literal text.

---

## 4. Counterexample Exposing the Rule's Limits

* **Claim:** `[claim_id]` — `[claim text]` (`[Posting Title]`)
* **Agent answer vs. My label:** Agent answered `[supported / I cannot tell]` | I labeled `[insufficient / contradicted / supported]`
* **Quoted sentence from posting:**
  > "[Exact sentence from claims.csv / posting text]"
* **How this exposes the limit:**
  * *[If Agent = `supported`, Mine = `insufficient` / `contradicted`:]* The agent relied on surface-level keyword matching (`"[matched term]"`) without checking modality, scope, or negation. Even though the target token appears verbatim, the sentence frames it as `[optional/preferred / handled by another team / negated]`, so the text does not actually entail the claim.
  * *[If Agent = `I cannot tell`, Mine = `supported`:]* My abstention rule instructs the agent not to guess beyond literal wording, which caused it to abstain when the posting avoided the exact keyword in the claim. However, the quoted sentence states the requirement in clear equivalent terms (`"[paraphrased phrase]"`), showing that strict lexical matching can cause unnecessary abstention on valid paraphrases.