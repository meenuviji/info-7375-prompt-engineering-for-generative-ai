"""Rule set "v3": FILTER.md as committed in 4923b21 (its header still says "v1").

Kept beside src/filter.py (old v1/v2) so the earlier audit and set A/B numbers stay
reproducible. Every rule is whole-word / whole-phrase, case-insensitive (\\b...\\b).

Rules (FILTER.md sections 1.1-1.4):
- R1-R4 on the title: 2 points each. R5 on the title: +1 only if some R1-R4 matched
  (rules_fired lists R5 only when it scores).
- T1-T5 on the description: +1 each, at most once per rule. FILTER.md states no cap.
  T3: "pipeline(s)" counts only when the word right before it is data/etl/elt/ml/ingestion.
  T5: only the listed phrases ("dashboards" plural; "forecasting" only as "demand forecasting").
- X1, X2, X4 on the title; X3 = location is clearly outside the US (src/location.py);
  X5 = the FILTER.md regex, used literally (decision 2026-11-25), or "phd/doctorate required".

Decision order (section 3 and decisions of 2026-11-25):
1. title missing                                   -> CANNOT_TELL
2. any of X1-X5 fired                              -> REJECTED
3. no R1-R4 match, or (description present, location known, and score < 5) -> REJECTED
4. description empty, or location ambiguous:
      REJECTED if the posting could not be KEPT anyway
      (with a description present: score < 5), else CANNOT_TELL
5. score >= 5                                      -> KEPT, else REJECTED
close_call: decided by score (not CANNOT_TELL) and either
  (no exclusion and score == 4) or (score >= 5 and the only exclusion is X3 or X5).
"""

import re
from dataclasses import dataclass

from . import config as cfg
from . import location as loc

CORE_ROLE_RULES = {
    "R1": ["data engineer", "analytics engineer"],
    "R2": ["data scientist", "applied scientist"],
    "R3": ["ai engineer", "ml engineer", "machine learning engineer"],
    "R4": ["bi analyst", "business intelligence analyst", "data analyst", "product analyst"],
}
R5_PHRASES = ["new grad", "new graduate", "entry level", "entry-level", "junior", "early career", "associate"]
TOPIC_RULES = {
    "T1": ["python", "pyspark"],
    "T2": ["sql", "bigquery", "snowflake", "redshift", "postgres"],
    "T3": ["etl", "elt", "airflow", "dbt", "kafka", "spark", "data pipeline", "data pipelines"],
    "T4": ["machine learning", "deep learning", "pytorch", "tensorflow", "scikit-learn", "llm", "rag"],
    "T5": ["tableau", "power bi", "looker", "dashboards", "a/b testing", "experimentation", "time series",
           "demand forecasting"],
}
T3_PIPELINE_PREFIXES = ["data", "etl", "elt", "ml", "ingestion"]
TITLE_EXCLUSIONS = {
    "X1": ["senior", "sr", "staff", "principal", "lead", "manager", "director", "head", "vp", "vice president",
           "chief"],
    "X2": ["intern", "internship", "co-op", "coop", "year at palantir"],
    "X4": ["account executive", "sales", "business development", "recruiter", "accounting", "finance",
           "financial systems", "investor relations", "gtm", "operations", "forward deployed",
           "deployment strategist", "developer advocate", "solutions architect", "customer engineer",
           "escalations", "security analyst"],
}
X5_EXPERIENCE = re.compile(
    r"\b([3-9]|1[0-9])\+?\s+years?\s+of\s+(industry\s+|professional\s+|relevant\s+)?experience", re.IGNORECASE)
X5_PHD = re.compile(r"\b(?:phd|doctorate)\s+required\b", re.IGNORECASE)


def _phrase(p: str) -> str:
    return r"\b" + r"\s+".join(re.escape(w) for w in p.split()) + r"\b"


def _compile(rules):
    return {k: re.compile("|".join(f"(?:{_phrase(p)})" for p in v), re.IGNORECASE) for k, v in rules.items()}


CORE_RE = _compile(CORE_ROLE_RULES)
R5_RE = _compile({"R5": R5_PHRASES})["R5"]
TOPIC_RE = _compile(TOPIC_RULES)
T3_PIPELINE_RE = re.compile(r"\b(?:" + "|".join(T3_PIPELINE_PREFIXES) + r")\s+pipelines?\b", re.IGNORECASE)
TITLE_X_RE = _compile(TITLE_EXCLUSIONS)


@dataclass(frozen=True)
class FilterResult:
    decision: str
    score: int
    rules_fired: tuple[str, ...]
    close_call: bool
    location_class: str = ""


def _topics(description: str) -> list[str]:
    out = []
    for rule, rx in TOPIC_RE.items():
        if rx.search(description) or (rule == "T3" and T3_PIPELINE_RE.search(description)):
            out.append(rule)
    return out


def evaluate(title: str, location: str, description: str) -> FilterResult:
    title = (title or "").strip()
    description = description or ""
    has_desc = bool(description.strip())
    if not title:
        return FilterResult(cfg.CANNOT_TELL, 0, ("NO_TITLE",), False)

    core = [r for r, rx in CORE_RE.items() if rx.search(title)]
    r5 = ["R5"] if core and R5_RE.search(title) else []
    topics = _topics(description) if has_desc else []
    loc_class, _ = loc.classify(location, description)

    exclusions = [x for x in ("X1", "X2", "X4") if TITLE_X_RE[x].search(title)]
    if loc_class == loc.NON_US:
        exclusions.append("X3")
    if has_desc and (X5_EXPERIENCE.search(description) or X5_PHD.search(description)):
        exclusions.append("X5")
    exclusions.sort()

    score = (cfg.V3_CORE_ROLE_POINTS * len(core) + cfg.V3_R5_POINT * len(r5)
             + cfg.V3_TOPIC_POINT * len(topics))
    markers = ([] if has_desc else ["NO_DESC"]) + (["LOC_AMBIGUOUS"] if loc_class == loc.AMBIGUOUS else [])
    rules = tuple(core + r5 + topics + exclusions + markers)

    close = ((not exclusions and score == cfg.V3_CLOSE_CALL_SCORE)
             or (score >= cfg.V3_KEEP_THRESHOLD and len(exclusions) == 1
                 and exclusions[0] in cfg.V3_CLOSE_CALL_BOUNDARY_RULES))

    if exclusions or not core:
        return FilterResult(cfg.REJECTED, score, rules, close, loc_class)
    unknown = not has_desc or loc_class == loc.AMBIGUOUS
    if unknown:
        could_be_kept = (not has_desc) or score >= cfg.V3_KEEP_THRESHOLD
        if could_be_kept:
            return FilterResult(cfg.CANNOT_TELL, score, rules, False, loc_class)
        return FilterResult(cfg.REJECTED, score, rules, close, loc_class)
    decision = cfg.KEPT if score >= cfg.V3_KEEP_THRESHOLD else cfg.REJECTED
    return FilterResult(decision, score, rules, close, loc_class)
