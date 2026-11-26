"""Tests for the FILTER.md v1 filter (wrong versions W1-W4 and boundaries), the loader,
make_sheets determinism, and label.py blindness. All offline; synthetic inputs only."""

import csv
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import label  # noqa: E402
import make_sheets  # noqa: E402
from src import config as cfg  # noqa: E402
from src.filter import evaluate  # noqa: E402
from src.postings import LoadReport, Posting, html_to_text, records_to_postings  # noqa: E402

TWO_TOPICS = "You will write Python and SQL."              # T1, T2
FOUR_TOPICS = "Python, SQL, Airflow pipelines, PyTorch."   # T1-T4
ALL_TOPICS = FOUR_TOPICS + " Tableau dashboards."          # T1-T5


# --- W1: whole-word matching, never substrings ------------------------------------------
@pytest.mark.parametrize("title", ["Maintenance Technician", "HTML Developer", "Mailroom Clerk",
                                   "Database Administrator", "Biologist"])
def test_w1_substrings_do_not_match_role_rules(title):
    r = evaluate(title, ALL_TOPICS)
    assert not any(rule.startswith("R") for rule in r.rules_fired)
    assert r.score == cfg.TOPIC_CAP and r.decision == cfg.REJECTED


@pytest.mark.parametrize("title,rule", [("ML Engineer", "R3"), ("Applied AI Engineer", "R3"),
                                        ("data ENGINEER", "R1"), ("Engineer, ML/AI Platform", "R3"),
                                        ("Business Intelligence Analyst", "R4")])
def test_w1_whole_words_match_case_insensitively(title, rule):
    assert rule in evaluate(title, TWO_TOPICS).rules_fired


def test_w1_topic_substrings_do_not_fire():
    # "sql" inside "MySQLish"? no boundary; "rag" inside "storage"/"leverage"; "etl" inside "Netlify".
    r = evaluate("Data Engineer", "We leverage storage on Netlify with MySQLish tools and a paragraph.")
    assert [x for x in r.rules_fired if x.startswith("T")] == []


def test_phrase_matches_across_line_break_but_not_partial_phrase():
    assert "R1" in evaluate("Data\nEngineer", TWO_TOPICS).rules_fired
    assert "T5" not in evaluate("Data Engineer", "time-of-day series").rules_fired


# --- W2: each topic rule counts once; topic part capped -----------------------------------
def test_w2_long_repetitive_posting_does_not_outrank_concise_one():
    long_body = ("We love data and python. " * 300) + "python " * 500
    verbose = evaluate("Data Engineer", long_body)
    concise = evaluate("Data Engineer", FOUR_TOPICS)
    assert verbose.score == cfg.ROLE_SCORE + 1 and verbose.decision == cfg.REJECTED
    assert concise.score == cfg.ROLE_SCORE + 4 and concise.decision == cfg.KEPT
    assert concise.score > verbose.score


def test_w2_topic_part_capped_at_four_even_with_five_rules():
    r = evaluate("Data Scientist", ALL_TOPICS)
    assert sum(x.startswith("T") for x in r.rules_fired) == 5
    assert r.score == cfg.ROLE_SCORE + cfg.TOPIC_CAP == 7


def test_multiple_role_rules_still_score_three():
    r = evaluate("Junior Data Engineer, Machine Learning", "")
    assert {"R1", "R3", "R5"} <= set(r.rules_fired)
    assert r.score == cfg.ROLE_SCORE


# --- threshold and close calls ------------------------------------------------------------
def test_threshold_boundary_four_rejected_five_kept():
    four = evaluate("Data Analyst", "Strong SQL required.")            # 3 + 1
    five = evaluate("Data Analyst", TWO_TOPICS)                        # 3 + 2
    assert (four.score, four.decision, four.close_call) == (4, cfg.REJECTED, True)
    assert (five.score, five.decision, five.close_call) == (5, cfg.KEPT, True)


def test_scores_outside_band_are_not_close_calls():
    assert evaluate("Data Analyst", "No tools named.").close_call is False      # 3
    assert evaluate("Data Analyst", ALL_TOPICS).close_call is False             # 7


def test_no_role_match_cannot_be_kept_even_with_all_topics():
    r = evaluate("Account Executive", ALL_TOPICS)
    assert r.score == 4 and r.decision == cfg.REJECTED and r.close_call is True


# --- W3: empty description -> CANNOT_TELL, not REJECTED -----------------------------------
@pytest.mark.parametrize("description", ["", "   \n\t ", None])
def test_w3_empty_description_with_role_match_is_cannot_tell(description):
    r = evaluate("New Grad Data Scientist", description)
    assert r.decision == cfg.CANNOT_TELL and r.close_call is False


def test_w3_empty_description_without_role_match_is_rejected():
    assert evaluate("Account Executive", "").decision == cfg.REJECTED


def test_w3_exclusion_still_wins_over_cannot_tell():
    assert evaluate("Data Science Intern", "").decision == cfg.REJECTED


# --- W4: exclusions on the title only ------------------------------------------------------
def test_w4_senior_in_body_does_not_exclude():
    r = evaluate("Data Engineer", "You will work with senior engineers and a staff manager. " + TWO_TOPICS)
    assert not any(x.startswith("X") for x in r.rules_fired)
    assert r.decision == cfg.KEPT


@pytest.mark.parametrize("title,rule", [("Senior Data Engineer", "X1"), ("Sr. Data Scientist", "X1"),
                                        ("Head of Data Science", "X1"), ("ML Engineering Manager", "X1"),
                                        ("Data Science Intern", "X2"), ("Data Engineering Co-op", "X2")])
def test_w4_title_exclusions_reject_regardless_of_score(title, rule):
    r = evaluate(title, ALL_TOPICS)
    assert rule in r.rules_fired and r.decision == cfg.REJECTED and r.close_call is False
    assert r.score == 7  # score still reported


def test_exclusion_words_do_not_match_inside_other_words():
    r = evaluate("Data Engineer, Headquarters Staffing Internal Tools", TWO_TOPICS)
    assert not any(x.startswith("X") for x in r.rules_fired)


# --- v2: "associate" removed from R5, nothing else changed ----------------------------------
def test_v2_associate_no_longer_a_role_match():
    v1 = evaluate("GTM Strategy/Operations Associate", FOUR_TOPICS, "v1")
    v2 = evaluate("GTM Strategy/Operations Associate", FOUR_TOPICS, "v2")
    assert "R5" in v1.rules_fired and v1.decision == cfg.KEPT
    assert "R5" not in v2.rules_fired and v2.score == cfg.TOPIC_CAP and v2.decision == cfg.REJECTED


@pytest.mark.parametrize("title,desc", [("New Grad Data Engineer", TWO_TOPICS), ("Junior Analyst", ""),
                                        ("Senior Data Scientist", ALL_TOPICS), ("Maintenance Technician", ""),
                                        ("Data Analyst", "Strong SQL required.")])
def test_v2_same_as_v1_without_associate(title, desc):
    assert evaluate(title, desc, "v1") == evaluate(title, desc, "v2")


def test_v2_associate_with_empty_description_is_rejected_not_cannot_tell():
    assert evaluate("Associate", "", "v1").decision == cfg.CANNOT_TELL
    assert evaluate("Associate", "", "v2").decision == cfg.REJECTED


# --- loader --------------------------------------------------------------------------------
def test_html_to_text_strips_escaped_tags_and_entities():
    raw = "&lt;div&gt;&lt;p&gt;Python &amp;amp; SQL&lt;/p&gt;&lt;p&gt;Use&amp;nbsp;dbt&lt;/p&gt;&lt;/div&gt;"
    assert html_to_text(raw) == "Python & SQL\nUse dbt"
    assert html_to_text(None) == ""


def test_records_dedup_by_provider_and_id_and_skip_missing_title():
    base = {"board": "b", "location": "", "description": "x"}
    recs = [dict(base, provider="greenhouse", id="1", title="A"),
            dict(base, provider="greenhouse", id="1", title="A again"),
            dict(base, provider="lever", id="1", title="Same id, other provider"),
            dict(base, provider="lever", id="2", title="")]
    report = LoadReport()
    postings = records_to_postings(recs, report)
    assert [(p.provider, p.id) for p in postings] == [("greenhouse", "1"), ("lever", "1")]
    assert postings[0].location == "unknown"
    assert (report.duplicates_dropped, report.skipped_no_title, report.loaded) == (1, 1, 2)


# --- make_sheets ---------------------------------------------------------------------------
def _synthetic_rows():
    rows = []
    for i in range(300):
        decision = cfg.KEPT if i % 10 == 0 else cfg.REJECTED
        rows.append({"provider": "greenhouse" if i % 2 else "lever", "board": f"b{i % 3}", "id": str(i),
                     "decision": decision, "close_call": "true" if i % 7 == 0 else "false"})
    return rows


def test_make_sheets_is_deterministic_with_seed():
    rows = _synthetic_rows()
    first = make_sheets.build_sets(rows, seed=cfg.SEED)
    assert first == make_sheets.build_sets(list(reversed(rows)), seed=cfg.SEED)  # order-independent
    assert first != make_sheets.build_sets(rows, seed=cfg.SEED + 1)


def test_make_sheets_sizes_no_overlap_and_blind():
    rows = _synthetic_rows()
    by_key = {(r["provider"], r["id"]): r for r in rows}
    set_a, set_b = make_sheets.build_sets(rows)
    assert len(set_a) == 40 and len(set_b) == 30
    keys_a = {(r["provider"], r["id"]) for r in set_a}
    keys_b = {(r["provider"], r["id"]) for r in set_b}
    assert len(keys_a) == 40 and len(keys_b) == 30 and not keys_a & keys_b
    why = [r["why_sampled"] for r in set_a]
    assert (why.count("random_rejected"), why.count("close_call"), why.count("random_kept")) == (30, 5, 5)
    for r in set_a:
        if r["why_sampled"] == "random_rejected":
            assert by_key[(r["provider"], r["id"])]["decision"] == cfg.REJECTED
    assert all(set(r) == set(make_sheets.KEY_COLUMNS) for r in set_a + set_b)


def test_make_sheets_takes_all_kept_when_fewer_than_five_and_kept_before_close_calls():
    rows = _synthetic_rows()
    for r in rows:
        r["decision"] = cfg.REJECTED
    for i in ("0", "7", "14", "20"):  # 4 KEPT; "0", "7" and "14" are also close calls
        next(r for r in rows if r["id"] == i)["decision"] = cfg.KEPT
    set_a, _ = make_sheets.build_sets(rows)
    kept_ids = {r["id"] for r in set_a if r["why_sampled"] == "random_kept"}
    assert kept_ids == {"0", "7", "14", "20"}
    assert len(set_a) == 39 and sum(r["why_sampled"] == "close_call" for r in set_a) == 5


# --- label.py never shows the filter output ------------------------------------------------
def test_label_tool_saves_each_answer_and_never_shows_decision(tmp_path):
    path = tmp_path / "labels.csv"
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=label.COLUMNS)
        w.writeheader()
        w.writerow({"id": "1", "provider": "lever", "my_verdict": "", "my_reason": ""})
        w.writerow({"id": "2", "provider": "lever", "my_verdict": "", "my_reason": ""})
    postings = {("lever", "1"): Posting("lever", "p", "1", "Data Engineer", "Remote", "x" * 2000),
                ("lever", "2"): Posting("lever", "p", "2", "Chef", "unknown", "")}
    answers = iter(["f", "y", "  builds   pipelines ", "q"])
    shown = []
    outcome = label.label_file(path, postings, ask=lambda _: next(answers),
                               show=lambda *a, **k: shown.append(" ".join(map(str, a))), clear=lambda: None)
    assert outcome == "quit"
    assert label.read_rows(path)[0] == {"id": "1", "provider": "lever", "my_verdict": "y",
                                        "my_reason": "builds pipelines"}
    text = "\n".join(shown)
    assert "x" * 2000 in text  # f showed the full description
    for word in ("KEPT", "REJECTED", "CANNOT_TELL", "score", "R1", "rules"):
        assert word not in text
