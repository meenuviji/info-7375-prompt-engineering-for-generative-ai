"""Tests for rule set v3 = FILTER.md as committed in 4923b21 (section 4 wrong versions 1-4,
plus R5 gating, X3 locations, X5, close calls). Offline; synthetic inputs only."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config as cfg  # noqa: E402
from src import location as loc  # noqa: E402
from src.filter_v3 import evaluate  # noqa: E402

US = "New York, NY"
TOPICS3 = "You will use Python and SQL to build Airflow jobs."   # T1, T2, T3


def fired(r, prefix):
    return [x for x in r.rules_fired if x.startswith(prefix)]


# --- W1: whole words only --------------------------------------------------------------------
@pytest.mark.parametrize("title", ["Maintenance Technician", "Email Specialist", "ISR Engineer", "Mailroom AIde"])
def test_w1_no_substring_role_or_exclusion_matches(title):
    r = evaluate(title, US, TOPICS3)
    assert fired(r, "R") == [] and "X1" not in r.rules_fired


def test_w1_topic_words_need_boundaries():
    r = evaluate("Data Engineer", US, "We leverage storage; our sparkle and Netlify pythonic tools.")
    assert fired(r, "T") == []


# --- W2: each topic rule at most +1 --------------------------------------------------------------
def test_w2_repetition_does_not_add_points():
    long = evaluate("Data Engineer", US, "python sql " * 500)
    short = evaluate("Data Engineer", US, TOPICS3)
    assert long.score == 2 + 2 and short.score == 2 + 3
    assert long.decision == cfg.REJECTED and short.decision == cfg.KEPT


def test_score_formula_stacks_core_roles_and_gated_r5():
    r = evaluate("Junior Data Engineer / Data Analyst", US, TOPICS3)
    assert fired(r, "R") == ["R1", "R4", "R5"] and r.score == 2 * 2 + 1 + 3


# --- W3: false friends need anchoring ------------------------------------------------------------
def test_w3_sales_pipeline_is_not_t3_but_data_pipeline_is():
    assert "T3" not in evaluate("Data Engineer", US, "Build a healthy sales pipeline.").rules_fired
    for text in ("Own the data pipeline.", "Maintain ETL pipelines.", "ML pipelines at scale.",
                 "ingestion pipeline work"):
        assert "T3" in evaluate("Data Engineer", US, text).rules_fired, text


def test_w3_revenue_forecasting_is_not_t5_but_demand_forecasting_is():
    assert "T5" not in evaluate("Data Scientist", US, "Ensure revenue and quota forecasting accuracy.").rules_fired
    assert "T5" in evaluate("Data Scientist", US, "Build demand forecasting models.").rules_fired


def test_w3_associate_without_core_role_scores_nothing():
    r = evaluate("Strategy Associate", US, TOPICS3 + " PyTorch dashboards")
    assert "R5" not in r.rules_fired and r.decision == cfg.REJECTED
    assert "R5" in evaluate("Associate Data Scientist", US, TOPICS3).rules_fired


# --- W4: missing description / ambiguous location -> CANNOT_TELL, never silent rejection --------
@pytest.mark.parametrize("description", ["", "   ", None])
def test_w4_empty_description_with_core_role_is_cannot_tell(description):
    r = evaluate("Data Engineer", US, description)
    assert r.decision == cfg.CANNOT_TELL and "NO_DESC" in r.rules_fired


def test_w4_hybrid_without_place_is_cannot_tell_when_otherwise_kept():
    r = evaluate("Data Engineer", "Hybrid", TOPICS3)
    assert r.decision == cfg.CANNOT_TELL and "LOC_AMBIGUOUS" in r.rules_fired


def test_hybrid_uses_available_location_line():
    us = evaluate("Data Engineer", "Hybrid", "Available Locations: Austin, TX\n" + TOPICS3)
    non_us = evaluate("Data Engineer", "Hybrid", "Available Location - Bengaluru, India\n" + TOPICS3)
    assert us.decision == cfg.KEPT
    assert non_us.decision == cfg.REJECTED and "X3" in non_us.rules_fired


def test_unknown_fields_do_not_rescue_postings_that_cannot_be_kept():
    assert evaluate("Data Engineer", "Hybrid", "Python only.").decision == cfg.REJECTED   # score 3
    assert evaluate("Chef", US, "").decision == cfg.REJECTED                              # no core role
    assert evaluate("Senior Data Engineer", "Hybrid", "").decision == cfg.REJECTED        # title exclusion


def test_missing_title_is_cannot_tell():
    assert evaluate("", US, TOPICS3).decision == cfg.CANNOT_TELL


# --- X3 location classes -----------------------------------------------------------------------
@pytest.mark.parametrize("text,expected", [
    ("New York, New York, USA", loc.US), ("Palo Alto, CA", loc.US), ("Washington, D.C.", loc.US),
    ("California, USA, Remote", loc.US), ("OH (can work remotely within the state)", loc.US),
    ("Austin", loc.US), ("London, United Kingdom", loc.NON_US), ("Singapore", loc.NON_US),
    ("Canada, Remote", loc.NON_US), ("Hybrid", loc.AMBIGUOUS), ("Distributed; Hybrid", loc.AMBIGUOUS),
    ("Remote", loc.AMBIGUOUS), ("North America", loc.AMBIGUOUS), ("", loc.AMBIGUOUS)])
def test_location_classes(text, expected):
    assert loc.classify_text(text) == expected


# --- exclusions --------------------------------------------------------------------------------
@pytest.mark.parametrize("title,rule", [("Lead Data Engineer", "X1"), ("Chief Data Scientist", "X1"),
                                        ("Data Engineer Intern", "X2"), ("Year at Palantir - Data", "X2"),
                                        ("Data Engineer - Talent Acquisition Operations", "X4"),
                                        ("Forward Deployed AI Engineer", "X4")])
def test_title_exclusions(title, rule):
    r = evaluate(title, US, TOPICS3)
    assert rule in r.rules_fired and r.decision == cfg.REJECTED


def test_x5_literal_regex_only():
    assert "X5" in evaluate("Data Engineer", US, TOPICS3 + " 3+ years of professional experience.").rules_fired
    assert "X5" in evaluate("Data Engineer", US, TOPICS3 + " PhD required.").rules_fired
    # Literal regex (decision 2026-11-25): these phrasings are NOT caught.
    assert "X5" not in evaluate("Data Engineer", US, TOPICS3 + " 4+ years experience.").rules_fired
    assert "X5" not in evaluate("Data Engineer", US, TOPICS3 + " 5+ years of data scientist experience.").rules_fired
    assert "X5" not in evaluate("Data Engineer", US, TOPICS3 + " 2 years of experience.").rules_fired


def test_seniority_in_description_does_not_exclude():
    r = evaluate("Data Engineer", US, TOPICS3 + " Work with senior engineers and a staff manager.")
    assert r.decision == cfg.KEPT


# --- close calls ---------------------------------------------------------------------------------
def test_close_call_score_four_without_exclusion():
    r = evaluate("Data Engineer", US, "Python and SQL.")   # 2 + 2
    assert (r.score, r.decision, r.close_call) == (4, cfg.REJECTED, True)


def test_close_call_score_five_rejected_only_by_x3_or_x5():
    only_x3 = evaluate("Data Engineer", "London, United Kingdom", TOPICS3)
    two = evaluate("Senior Data Engineer", "London, United Kingdom", TOPICS3)
    assert only_x3.close_call is True and only_x3.decision == cfg.REJECTED
    assert two.close_call is False


def test_kept_posting_is_not_a_close_call_above_band():
    r = evaluate("Data Engineer", US, TOPICS3 + " PyTorch, Tableau.")
    assert (r.decision, r.score, r.close_call) == (cfg.KEPT, 7, False)
