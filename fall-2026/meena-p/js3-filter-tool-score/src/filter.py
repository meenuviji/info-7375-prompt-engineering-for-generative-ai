"""The JS3 filter, implemented exactly as FILTER.md section 1 (v1, and v2 = v1 minus
"associate" in R5; choose with evaluate(..., version=)).

Matching (every rule): whole word or whole phrase, case-insensitive, word boundaries
(\\b...\\b). Never substring matching (W1). A space inside a phrase matches any run of
whitespace, so "data\\nengineer" still counts as the phrase.

Scope: role rules R1-R5 and exclusion rules X1-X2 look at the title only (W4);
topic rules T1-T5 look at the description only, each rule counted at most once (W2).

Decision order:
1. any exclusion rule matches the title          -> REJECTED (score still reported)
2. a role rule matches and description is empty  -> CANNOT_TELL (W3)
3. score >= KEEP_THRESHOLD                       -> KEPT
4. otherwise                                     -> REJECTED
close_call is true only for decisions made by score (steps 3-4) when the score is in
CLOSE_CALL_SCORES.
"""

import re
from dataclasses import dataclass

from . import config as cfg

# Copied word for word from FILTER.md v1, sections 1.1-1.3.
ROLE_RULES = {
    "R1": ["data engineer", "data engineering", "analytics engineer"],
    "R2": ["data scientist", "data science"],
    "R3": ["machine learning", "ML", "AI engineer", "applied AI"],
    "R4": ["business intelligence", "BI engineer", "BI analyst", "data analyst"],
    "R5": ["new grad", "university grad", "early career", "associate", "junior", "entry level"],
}
TOPIC_RULES = {
    "T1": ["python", "pandas", "pyspark"],
    "T2": ["sql", "snowflake", "bigquery", "postgresql", "redshift"],
    "T3": ["pipeline", "pipelines", "ETL", "ELT", "airflow", "dbt", "kafka"],
    "T4": ["machine learning", "deep learning", "pytorch", "tensorflow", "scikit-learn", "NLP", "RAG"],
    "T5": ["time series", "forecasting", "tableau", "power bi", "dashboard", "dashboards"],
}
EXCLUSION_RULES = {
    "X1": ["senior", "sr", "staff", "principal", "distinguished", "director", "head", "manager",
           "vp", "vice president"],
    "X2": ["intern", "internship", "co-op"],
}


# FILTER.md v2 (2026-11-25): the only change is "associate" removed from R5.
ROLE_RULES_V2 = {**ROLE_RULES, "R5": ["new grad", "university grad", "early career", "junior", "entry level"]}


def phrase_pattern(phrase: str) -> str:
    words = [re.escape(w) for w in phrase.split()]
    return r"\b" + r"\s+".join(words) + r"\b"


def compile_rules(rules: dict[str, list[str]]) -> dict[str, re.Pattern]:
    return {rule_id: re.compile("|".join(f"(?:{phrase_pattern(p)})" for p in phrases), re.IGNORECASE)
            for rule_id, phrases in rules.items()}


ROLE_RE = compile_rules(ROLE_RULES)
TOPIC_RE = compile_rules(TOPIC_RULES)
EXCLUSION_RE = compile_rules(EXCLUSION_RULES)
ROLE_RE_BY_VERSION = {"v1": ROLE_RE, "v2": compile_rules(ROLE_RULES_V2)}
VERSIONS = tuple(ROLE_RE_BY_VERSION)


def fired(compiled: dict[str, re.Pattern], text: str) -> list[str]:
    return [rule_id for rule_id, rx in compiled.items() if rx.search(text or "")]


@dataclass(frozen=True)
class FilterResult:
    decision: str
    score: int
    rules_fired: tuple[str, ...]
    close_call: bool


def evaluate(title: str, description: str, version: str = "v1") -> FilterResult:
    """version selects the FILTER.md rule set; v1 stays the default so v1 results reproduce."""
    roles = fired(ROLE_RE_BY_VERSION[version], title)
    exclusions = fired(EXCLUSION_RE, title)
    has_description = bool((description or "").strip())
    topics = fired(TOPIC_RE, description) if has_description else []

    role_part = cfg.ROLE_SCORE if roles else 0
    topic_part = min(len(topics) * cfg.TOPIC_POINT, cfg.TOPIC_CAP)
    score = role_part + topic_part
    rules = tuple(roles + topics + exclusions)

    if exclusions:
        return FilterResult(cfg.REJECTED, score, rules, False)
    if roles and not has_description:
        return FilterResult(cfg.CANNOT_TELL, score, rules, False)
    decision = cfg.KEPT if score >= cfg.KEEP_THRESHOLD else cfg.REJECTED
    return FilterResult(decision, score, rules, score in cfg.CLOSE_CALL_SCORES)
