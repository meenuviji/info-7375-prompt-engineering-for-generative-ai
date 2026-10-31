"""Judge and validator tests. Postings and model responses here are CONSTRUCTED fixtures;
no API or CLI calls are made."""

import json
from pathlib import Path

import pytest

from agent import claude_judge, rule_judge
from agent.run import run
from agent.validate import check_alignment, validate_justification
from agent.validator import validate_claude_output
from agent.persona import get_path

ROOT = Path(__file__).resolve().parent.parent
PERSONA = json.loads((ROOT / "resume/persona.json").read_text())
POSTING = {"id": 4242, "title": "Data Engineer", "location": {"name": "Remote - US"},
           "content": "Python and SQL required."}

VALID = ('{"posting_id": "4242", "verdict": "relevant", '
         '"resume_fields": ["resume.skills.languages"], '
         '"posting_fields": ["posting.title", "posting.content"], '
         '"justification": "\\"Data Engineer\\" matches; posting.content asks for '
         'resume.skills.languages."}')


def obj(**over):
    o = json.loads(VALID)
    o.update(over)
    return json.dumps(o)


# validator: accepts exactly the contract shape ---------------------------------

def test_validator_accepts_valid_output():
    parsed, errors = validate_claude_output(VALID, POSTING, PERSONA)
    assert errors == []
    assert parsed == json.loads(VALID)  # returned as-is, not rewritten


# validator: rejects each malformed case (hand-written fixture strings) ----------

MALFORMED = {
    "prose": "This posting is relevant because the candidate knows Python.",
    "code_fence": "```json\n" + VALID + "\n```",
    "prose_then_json": "Here is my answer:\n" + VALID,
    "json_then_prose": VALID + "\nHope this helps!",
    "truncated": VALID[:-5],
    "empty": "",
    "json_array": "[" + VALID + "]",
    "json_string": json.dumps(VALID),
    "extra_key": obj(confidence=0.9),
    "missing_key": json.dumps({k: v for k, v in json.loads(VALID).items()
                               if k != "posting_fields"}),
    "duplicate_key": VALID[:-1] + ', "verdict": "not_relevant"}',
    "verdict_capitalized": obj(verdict="Relevant"),
    "verdict_other": obj(verdict="maybe"),
    "verdict_relevant_space": obj(verdict="not relevant"),
    "posting_id_mismatch": obj(posting_id="4243"),
    "posting_id_int": obj(posting_id=4242),
    "resume_fields_empty": obj(resume_fields=[]),
    "posting_fields_empty": obj(posting_fields=[]),
    "resume_fields_not_list": obj(resume_fields="resume.skills"),
    "resume_field_missing": obj(resume_fields=["resume.years_experience"]),
    "resume_field_bad_index": obj(resume_fields=["resume.experience.5.title"]),
    "posting_field_missing": obj(posting_fields=["posting.seniority"]),
    "posting_field_unprefixed": obj(posting_fields=["title"]),
    "resume_path_in_posting_list": obj(posting_fields=["resume.skills"]),
    "justification_cites_fake_field": obj(
        justification='"Data Engineer" fits resume.personal.target_title.'),
    "justification_empty": obj(justification="  "),
}


@pytest.mark.parametrize("name", MALFORMED)
def test_validator_rejects_malformed(name):
    parsed, errors = validate_claude_output(MALFORMED[name], POSTING, PERSONA)
    assert parsed is None
    assert errors, name


def test_validator_names_the_specific_problem():
    _, e = validate_claude_output(MALFORMED["posting_field_missing"], POSTING, PERSONA)
    assert e == ["cited field does not exist: posting.seniority"]
    _, e = validate_claude_output(MALFORMED["posting_id_mismatch"], POSTING, PERSONA)
    assert "does not match posting sent 4242" in e[0]


# claude judge: retry once, then INVALID with raw text; no coercion ------------

def fake_call(responses):
    """CONSTRUCTED stand-in for the model: returns the given strings in order."""
    it = iter(responses)
    calls = []
    def call(prompt, model, system):
        calls.append((prompt, model, system))
        return next(it), {"model_reported": ["fake"]}
    call.calls = calls
    return call


def test_invalid_twice_records_INVALID_with_raw(tmp_path):
    bad = [MALFORMED["code_fence"], MALFORMED["prose"]]
    call = fake_call(bad)
    r = claude_judge.judge(POSTING, PERSONA, call=call, log_path=tmp_path / "log.jsonl")
    assert len(call.calls) == 2
    assert r["verdict"] == "INVALID"
    assert r["raw_text"] == bad
    assert r["kind"] == "JUDGMENT"


def test_retry_once_then_valid(tmp_path):
    call = fake_call([MALFORMED["extra_key"], VALID])
    r = claude_judge.judge(POSTING, PERSONA, call=call, log_path=tmp_path / "log.jsonl")
    assert r["verdict"] == "relevant" and r["attempts"] == 2
    assert r["justification"] == json.loads(VALID)["justification"]


def test_no_third_attempt(tmp_path):
    call = fake_call([MALFORMED["prose"], MALFORMED["prose"], VALID])
    r = claude_judge.judge(POSTING, PERSONA, call=call, log_path=tmp_path / "log.jsonl")
    assert r["verdict"] == "INVALID" and len(call.calls) == 2


def test_fenced_json_is_not_repaired(tmp_path):
    call = fake_call([MALFORMED["code_fence"]] * 2)
    r = claude_judge.judge(POSTING, PERSONA, call=call, log_path=tmp_path / "log.jsonl")
    assert r["verdict"] == "INVALID"  # would be "relevant" if fences were stripped


def test_every_call_logged(tmp_path, monkeypatch):
    monkeypatch.delenv("JUDGE_MODEL", raising=False)
    log = tmp_path / "log.jsonl"
    claude_judge.judge(POSTING, PERSONA, call=fake_call([MALFORMED["prose"], VALID]),
                       log_path=log)
    lines = [json.loads(l) for l in log.read_text().splitlines()]
    assert len(lines) == 2
    for l in lines:
        assert l["ts_utc"].endswith("Z")
        assert l["model"] == "claude-sonnet-5-5"
        assert l["prompt_file"] == "judge_v1.txt"
        assert l["system_prompt_file"] == "system_v1.txt"
        assert "raw_response" in l
    assert lines[0]["validator"]["ok"] is False and lines[0]["raw_response"] == MALFORMED["prose"]
    assert lines[1]["validator"] == {"ok": True, "errors": []}


def test_model_from_env_is_used_and_recorded(tmp_path, monkeypatch):
    monkeypatch.setenv("JUDGE_MODEL", "claude-haiku-5-5")
    call = fake_call([VALID])
    r = claude_judge.judge(POSTING, PERSONA, call=call, log_path=tmp_path / "log.jsonl")
    assert call.calls[0][1] == "claude-haiku-5-5"
    assert r["model"] == "claude-haiku-5-5" and r["model_source"] == "env JUDGE_MODEL"


def test_system_prompt_loaded_from_file_verbatim(tmp_path):
    call = fake_call([VALID, VALID])
    r = claude_judge.judge(POSTING, PERSONA, call=call, log_path=tmp_path / "log.jsonl")
    # Exact text that was hard-coded before it moved to prompts/system_v1.txt.
    assert call.calls[0][2] == "You are a strict classifier. Follow the user's instructions exactly."
    assert r["system_prompt_file"] == "system_v1.txt"
    alt = tmp_path / "system_v2.txt"
    alt.write_text("ALT")
    claude_judge.judge(POSTING, PERSONA, call=call, system_path=alt,
                       log_path=tmp_path / "log.jsonl")
    assert call.calls[1][2] == "ALT"


def test_no_hard_coded_prompt_text_in_judge():
    src = (ROOT / "agent/claude_judge.py").read_text()
    assert "strict classifier" not in src


def test_default_model_when_env_unset(monkeypatch):
    monkeypatch.delenv("JUDGE_MODEL", raising=False)
    assert claude_judge.judge_model() == ("claude-sonnet-5-5", "default (JUDGE_MODEL not set)")


def test_prompt_contains_only_this_posting():
    p = claude_judge.build_prompt((ROOT / "prompts/judge_v1.txt").read_text(), POSTING, PERSONA)
    assert '"4242"' in p and "{{" not in p
    assert '"title": "Data Engineer"' in p


# rule judge: CONTRACT.md "The rule" -------------------------------------------

def post(title, loc, pid=1):
    return {"id": pid, "title": title, "location": {"name": loc}}


def test_persona_city_is_boston():
    assert rule_judge.persona_city(PERSONA) == "Boston"


@pytest.mark.parametrize("title,loc,verdict,failed", [
    ("Data Engineer", "Remote - US", "relevant", None),
    ("machine learning engineer", "Boston, MA", "relevant", None),   # clause 1 case-insensitive
    ("AI Engineer, Platform", "Austin, TX", "not_relevant", "2"),
    ("Account Executive", "Remote", "not_relevant", "1"),
    ("Senior Data Engineer", "Remote", "not_relevant", "3"),
    ("Sr. ML Engineer", "Boston", "not_relevant", "3"),
    ("Engineering Manager, Data Engineer", "Austin", "not_relevant", "2, 3"),
    ("Recruiter", "London", "not_relevant", "1, 2"),
])
def test_rule(title, loc, verdict, failed):
    r = rule_judge.judge(post(title, loc), PERSONA)
    assert r["verdict"] == verdict and r["kind"] == "RECORD"
    if failed:
        assert f"clause {failed} failed" in r["justification"]
    else:
        assert "all three clauses passed" in r["justification"]


def test_rule_is_deterministic():
    p = post("Data Engineer", "Remote")
    assert rule_judge.judge(p, PERSONA) == rule_judge.judge(p, PERSONA)


@pytest.mark.parametrize("title,loc", [("Data Engineer", "Remote"),
                                       ("Senior Recruiter", "London")])
def test_rule_citations_valid_and_aligned(title, loc):
    p = post(title, loc, pid=77)
    r = rule_judge.judge(p, PERSONA)
    assert validate_justification(r["justification"], PERSONA, p) == []
    assert check_alignment([{"posting_id": 77, "rule_justification": r["justification"]}],
                           [p]) == []


# run.py wiring -----------------------------------------------------------------

def test_run_judges_new_postings_only(tmp_path, monkeypatch):
    monkeypatch.delenv("JUDGE_MODEL", raising=False)
    monkeypatch.setattr(claude_judge, "CALLS_LOG", tmp_path / "calls.jsonl")
    st, runs = tmp_path / "s.json", tmp_path / "runs"
    p1 = tmp_path / "1.json"
    p1.write_text(json.dumps({"jobs": [post("Recruiter", "Remote", 1)]}))
    p2 = tmp_path / "2.json"
    p2.write_text(json.dumps({"jobs": [post("Recruiter", "Remote", 1), POSTING]}))
    persona_path = ROOT / "resume/persona.json"
    run("a", p1, st, persona_path, runs)
    call = fake_call([VALID])
    r = run("b", p2, st, persona_path, runs, judge=True, claude_call=call)
    v = json.loads(Path(r["verdicts_output"]).read_text())
    assert Path(r["verdicts_output"]).name.endswith("_b_verdicts.json")
    assert [x["posting_id"] for x in v["verdicts"]] == [4242]
    x = v["verdicts"][0]
    assert x["rule_verdict"] == "relevant" and x["rule"]["kind"] == "RECORD"
    assert x["claude_verdict"] == "relevant" and x["claude"]["kind"] == "JUDGMENT"
    assert v["judge_model"] == "claude-sonnet-5-5"
    assert v["alignment_errors"] == []
    assert len((tmp_path / "calls.jsonl").read_text().splitlines()) == 1


def test_tests_never_write_real_evidence_log():
    # Guard: run last in this file; the real log must only hold real calls.
    real = ROOT / "evidence/claude_calls.jsonl"
    if real.exists():
        assert all(json.loads(l)["backend"] != "injected"
                   for l in real.read_text().splitlines())


def test_max_attempts_one_makes_exactly_one_call(tmp_path):
    call = fake_call([MALFORMED["prose"], VALID])
    log = tmp_path / "log.jsonl"
    r = claude_judge.judge(POSTING, PERSONA, call=call, log_path=log, max_attempts=1,
                           tag="sampling")
    assert len(call.calls) == 1 and r["verdict"] == "INVALID" and r["attempts"] == 1
    assert json.loads(log.read_text())["tag"] == "sampling"


# Gap 3: every path segment, including list indexes, is checked ------------------

@pytest.mark.parametrize("path", ["resume.experience.7.title", "resume.experience.0.nope",
                                  "resume.education.1.degree"])
def test_text_validator_rejects_made_up_indexed_path(path):
    text = f'"Data Engineer" posting.title vs {path}'
    assert f"cited field does not exist: {path}" in validate_justification(text, PERSONA, POSTING)


def test_claude_validator_rejects_made_up_indexed_path_in_text():
    raw = obj(justification='"Data Engineer" posting.title vs resume.experience.7.title')
    parsed, errors = validate_claude_output(raw, POSTING, PERSONA)
    assert parsed is None
    assert "cited field does not exist: resume.experience.7.title" in errors


def test_real_indexed_path_in_text_passes():
    text = '"Data Engineer" posting.title vs resume.experience.0.title.'
    assert validate_justification(text, PERSONA, POSTING) == []


# Gap 2: state is written only after both judges produced output for every new posting --

def test_state_not_updated_when_judging_fails(tmp_path):
    st, runs = tmp_path / "s.json", tmp_path / "runs"
    persona_path = ROOT / "resume/persona.json"
    p1 = tmp_path / "1.json"
    p1.write_text(json.dumps({"jobs": [post("Recruiter", "Remote", 1)]}))
    second = {**POSTING, "id": 4243}
    p2 = tmp_path / "2.json"
    p2.write_text(json.dumps({"jobs": [post("Recruiter", "Remote", 1), POSTING, second]}))
    run("a", p1, st, persona_path, runs)
    before = st.read_text()

    def fail_on_second(prompt, model, system):
        """CONSTRUCTED: valid for the first new posting, then the backend dies."""
        if '"4243"' in prompt:
            raise RuntimeError("judge backend failed")
        return VALID, {"model_reported": ["fake"]}

    with pytest.raises(RuntimeError):
        run("b", p2, st, persona_path, runs, judge=True, claude_call=fail_on_second)
    assert st.read_text() == before  # both new postings must still be reported as new next run


def test_state_updated_after_judging_succeeds(tmp_path):
    st, runs = tmp_path / "s.json", tmp_path / "runs"
    persona_path = ROOT / "resume/persona.json"
    p1 = tmp_path / "1.json"
    p1.write_text(json.dumps({"jobs": [post("Recruiter", "Remote", 1)]}))
    p2 = tmp_path / "2.json"
    p2.write_text(json.dumps({"jobs": [post("Recruiter", "Remote", 1), POSTING]}))
    run("a", p1, st, persona_path, runs)
    run("b", p2, st, persona_path, runs, judge=True, claude_call=fake_call([VALID]))
    assert json.loads(st.read_text()) == {"seen_ids": [1, 4242]}


# Audit row 2: a posting with no location name must not cite posting.location.name ------

@pytest.mark.parametrize("posting", [
    {"id": 91, "title": "Data Engineer"},                          # no location key
    {"id": 92, "title": "Data Engineer", "location": None},       # null location
    {"id": 93, "title": "Data Engineer", "location": {}},         # location without name
])
def test_rule_without_location_cites_only_existing_fields(posting):
    r = rule_judge.judge(posting, PERSONA)
    assert r["verdict"] == "not_relevant" and "clause 2 failed" in r["justification"]
    assert validate_justification(r["justification"], PERSONA, posting) == []
    for path in r["cited_posting_fields"] + r["cited_resume_fields"]:
        root, _, rest = path.partition(".")
        get_path({"posting": posting, "resume": PERSONA}[root], rest)  # raises if missing
