"""All posting data in this file is CONSTRUCTED fake data for tests, not from any board."""

import copy
import json
from pathlib import Path

import pytest

from agent import fetch, persona, state
from agent.run import run
from agent.validate import check_alignment, validate_justification

ROOT = Path(__file__).resolve().parent.parent


def board(*jobs):
    return {"jobs": [{"id": i, "title": t, "location": {"name": loc}} for i, t, loc in jobs],
            "meta": {"total": len(jobs)}}


@pytest.fixture
def priya():
    return json.loads((ROOT / "resume/persona.json").read_text())


# (a) allow-list ---------------------------------------------------------------

@pytest.mark.parametrize("url", [
    "https://evil.example.com/v1/boards/cloudflare/jobs",
    "https://boards-api.greenhouse.io.evil.com/v1/boards/x/jobs",
    "https://api.lever.co/v0/postings/cloudflare",
    "http://boards-api.greenhouse.io/v1/boards/cloudflare/jobs",  # not https
])
def test_allow_list_rejects_other_hosts_before_network(url, monkeypatch, tmp_path):
    def no_network(*a, **k):
        raise AssertionError("network call made for disallowed host")
    monkeypatch.setattr(fetch.requests, "get", no_network)
    with pytest.raises(fetch.HostNotAllowedError):
        fetch.fetch_board("test", url=url, raw_dir=tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_allow_list_contains_only_greenhouse():
    assert fetch.ALLOWED_HOSTS == {"boards-api.greenhouse.io"}
    fetch.check_allowed(fetch.BOARD_URL)  # does not raise


def test_fetch_saves_raw_bytes_unmodified(monkeypatch, tmp_path):
    body = b'{"jobs": [],   "meta": {"total": 0}}'  # odd spacing must survive
    class Resp:
        status_code = 200
        content = body
        def raise_for_status(self): pass
    monkeypatch.setattr(fetch.requests, "get", lambda *a, **k: Resp())
    path = fetch.fetch_board("t", raw_dir=tmp_path)
    assert path.read_bytes() == body
    assert path.name.endswith("_t.json")


# (b) baseline -----------------------------------------------------------------

def _write(tmp_path, name, data):
    p = tmp_path / name
    p.write_text(json.dumps(data))
    return p


def test_baseline_reports_zero_new_and_writes_state(tmp_path):
    src = _write(tmp_path, "b.json", board((1, "A", "Remote"), (2, "B", "Austin")))
    st = tmp_path / "state/seen_ids.json"
    r = run("base", src, st, ROOT / "resume/persona.json", tmp_path / "runs")
    assert r["baseline"] is True
    assert r["new_count"] == 0 and r["new_postings"] == []
    assert json.loads(st.read_text()) == {"seen_ids": [1, 2]}


def test_second_run_reports_only_added_ids(tmp_path):
    st = tmp_path / "seen.json"
    p1 = _write(tmp_path, "1.json", board((1, "A", "Remote")))
    p2 = _write(tmp_path, "2.json", board((1, "A", "Remote"), (7, "B", "Remote")))
    run("one", p1, st, ROOT / "resume/persona.json", tmp_path / "runs")
    r = run("two", p2, st, ROOT / "resume/persona.json", tmp_path / "runs")
    assert r["baseline"] is False
    assert [j["id"] for j in r["new_postings"]] == [7]


# (c) + wrong version 3: new-since-last is by id, not title ---------------------

def new_by_title_WRONG(prev_board, cur_board):
    """CONSTRUCTED wrong implementation: wrong version 3 from CONTRACT.md."""
    seen_titles = {j["title"] for j in prev_board["jobs"]}
    return sorted(j["id"] for j in cur_board["jobs"] if j["title"] not in seen_titles)


def new_by_id(prev_board, cur_board):
    return state.new_ids(state.posting_ids(cur_board), set(state.posting_ids(prev_board)))


def check_new_is_by_id(impl):
    prev = board((100, "Data Engineer", "Remote"))
    # Same title, different id: a genuinely new posting.
    cur = board((100, "Data Engineer", "Remote"), (200, "Data Engineer", "Remote"))
    assert impl(prev, cur) == [200]
    # Same id, retitled: not new.
    retitled = board((100, "Data Engineer II", "Remote"))
    assert impl(prev, retitled) == []


def test_new_is_by_id_not_title():
    check_new_is_by_id(new_by_id)


def test_check_catches_new_by_title():
    with pytest.raises(AssertionError):
        check_new_is_by_id(new_by_title_WRONG)


# (d) persona validator ---------------------------------------------------------

def test_real_persona_file_passes(priya):
    persona.validate_persona(priya)


def test_persona_rejects_non_example_email(priya):
    bad = copy.deepcopy(priya)
    bad["personal"]["email"] = "priya.nair@gmail.com"
    with pytest.raises(persona.PersonaError, match="email"):
        persona.validate_persona(bad)


def test_persona_rejects_non_555_phone(priya):
    bad = copy.deepcopy(priya)
    bad["personal"]["phone"] = "(555) 432-0163"
    with pytest.raises(persona.PersonaError, match="phone"):
        persona.validate_persona(bad)


def test_persona_rejects_email_hidden_elsewhere(priya):
    bad = copy.deepcopy(priya)
    bad["projects"][0]["bullets"].append("Contact: someone@northeastern.edu")
    with pytest.raises(persona.PersonaError, match="email"):
        persona.validate_persona(bad)


@pytest.mark.parametrize("field", ["location", "skills"])
def test_persona_rejects_missing_required_field(priya, field):
    bad = copy.deepcopy(priya)
    if field == "location":
        del bad["personal"]["location"]
    else:
        del bad["skills"]
    with pytest.raises(persona.PersonaError, match="missing"):
        persona.validate_persona(bad)


def test_refusal_message_does_not_leak_values(priya):
    bad = copy.deepcopy(priya)
    bad["personal"]["email"] = "leak@gmail.com"
    with pytest.raises(persona.PersonaError) as e:
        persona.validate_persona(bad)
    assert "leak@gmail.com" not in str(e.value)


def test_run_refuses_bad_persona_before_fetch(priya, tmp_path, monkeypatch):
    bad = copy.deepcopy(priya)
    bad["personal"]["phone"] = "555-432-0163"
    pp = _write(tmp_path, "p.json", bad)
    monkeypatch.setattr(fetch, "fetch_board",
                        lambda *a, **k: pytest.fail("fetched with invalid persona"))
    with pytest.raises(persona.PersonaError):
        run("x", None, tmp_path / "s.json", pp, tmp_path / "runs")
    assert not (tmp_path / "s.json").exists()


# (e) wrong versions 1 and 2, against CONSTRUCTED fake verdicts ----------------

POSTINGS = board((11, "Data Engineer", "Remote - US"),
                 (12, "Senior ML Engineer", "Austin, TX"),
                 (13, "Account Executive", "Boston, MA"))["jobs"]


def judge_ALIGNED(postings):
    """CONSTRUCTED fake judge with correct pairing (stand-in until the real rule judge)."""
    return [{"posting_id": p["id"], "rule_verdict": "not_relevant",
             "rule_justification": f'`posting.title` "{p["title"]}" vs `resume.skills`.'}
            for p in postings]


def judge_OFF_BY_ONE_WRONG(postings):
    """CONSTRUCTED wrong implementation: wrong version 1 (off-by-one zip)."""
    texts = [f'`posting.title` "{p["title"]}" vs `resume.skills`.' for p in postings]
    texts = texts[1:] + texts[:1]
    return [{"posting_id": p["id"], "rule_verdict": "not_relevant", "rule_justification": t}
            for p, t in zip(postings, texts)]


def check_aligned(judge):
    assert check_alignment(judge(POSTINGS), POSTINGS) == []


def test_alignment_passes_correct_pairing():
    check_aligned(judge_ALIGNED)


def test_alignment_catches_off_by_one():
    with pytest.raises(AssertionError):
        check_aligned(judge_OFF_BY_ONE_WRONG)
    errs = check_alignment(judge_OFF_BY_ONE_WRONG(POSTINGS), POSTINGS)
    assert len(errs) == 3


def judge_NEXT_ID_WRONG(postings):
    """CONSTRUCTED wrong implementation: wrong version 1, each verdict tagged with the
    next posting's id while its justification quotes the current posting's title."""
    n = len(postings)
    return [{"posting_id": postings[(i + 1) % n]["id"], "rule_verdict": "not_relevant",
             "rule_justification": f'`posting.title` "{p["title"]}" vs `resume.skills`.'}
            for i, p in enumerate(postings)]


def test_alignment_catches_verdict_paired_with_next_id():
    with pytest.raises(AssertionError):
        check_aligned(judge_NEXT_ID_WRONG)
    verdicts = judge_NEXT_ID_WRONG(POSTINGS)
    errs = check_alignment(verdicts, POSTINGS)
    assert len(errs) == len(POSTINGS)
    titles = {p["id"]: p["title"] for p in POSTINGS}
    for v, err in zip(verdicts, errs):
        own = f'"{titles[v["posting_id"]]}"'
        assert own not in v["rule_justification"]  # quoted title belongs to another id
        assert err == f'{v["posting_id"]}: rule_justification does not quote its own title {own}'


def test_alignment_checks_claude_justification_too():
    v = judge_ALIGNED(POSTINGS)
    v[0]["claude_justification"] = f'`posting.title` "{POSTINGS[1]["title"]}" `resume.skills`'
    assert len(check_alignment(v, POSTINGS)) == 1


POSTING = POSTINGS[0]


def test_validator_accepts_real_citations(priya):
    text = ('Clause 2 passed: `posting.location.name` "Remote - US" contains "Remote"; '
            '`resume.personal.location` is Boston, MA. `posting.title`.')
    assert validate_justification(text, priya, POSTING) == []


def justify_EMPTY_WRONG(resume, posting):
    """CONSTRUCTED wrong implementation: wrong version 2a, names no field."""
    return "Looks like a good fit for the candidate."


def justify_FAKE_FIELD_WRONG(resume, posting):
    """CONSTRUCTED wrong implementation: wrong version 2b, cites nonexistent fields."""
    return "`resume.years_experience` is 3 and `posting.seniority` is junior."


def justify_HALF_FAKE_WRONG(resume, posting):
    """CONSTRUCTED wrong implementation: one real field, one fake nested field."""
    return "`posting.title` matches `resume.personal.target_title`."


def justify_RESUME_ONLY_WRONG(resume, posting):
    """CONSTRUCTED wrong implementation: cites no posting field."""
    return "`resume.skills` includes Python."


def check_justifier(justify, resume):
    assert validate_justification(justify(resume, POSTING), resume, POSTING) == []


@pytest.mark.parametrize("wrong", [justify_EMPTY_WRONG, justify_FAKE_FIELD_WRONG,
                                   justify_HALF_FAKE_WRONG, justify_RESUME_ONLY_WRONG])
def test_validator_catches_bad_citations(wrong, priya):
    with pytest.raises(AssertionError):
        check_justifier(wrong, priya)


def test_validator_names_the_fake_field(priya):
    errs = validate_justification(justify_FAKE_FIELD_WRONG(priya, POSTING), priya, POSTING)
    assert "cited field does not exist: resume.years_experience" in errs
    assert "cited field does not exist: posting.seniority" in errs


# Gap 1: a redirect must not carry the fetch off the allow-list ----------------------

def _fake_transport(monkeypatch, hops):
    """CONSTRUCTED transport: requests' real redirect logic runs; only the socket is faked.
    hops maps URL -> (status, location or None, body)."""
    import requests
    sent = []

    def send(self, request, **kwargs):
        sent.append(request.url)
        status, location, body = hops[request.url]
        r = requests.Response()
        r.status_code, r.url, r.request = status, request.url, request
        r._content, r._content_consumed = body, True
        if location:
            r.headers["Location"] = location
        return r
    monkeypatch.setattr(requests.adapters.HTTPAdapter, "send", send)
    return sent


@pytest.mark.parametrize("status", [301, 302, 307])
def test_fetch_refuses_redirect_off_allow_list(status, monkeypatch, tmp_path):
    evil = "https://evil.example.com/jobs"
    sent = _fake_transport(monkeypatch, {
        fetch.BOARD_URL: (status, evil, b""),
        evil: (200, None, b'{"jobs": [{"id": 666, "title": "planted"}]}'),
    })
    with pytest.raises(fetch.HostNotAllowedError):
        fetch.fetch_board("t", raw_dir=tmp_path)
    assert evil not in sent          # never contacted the off-list host
    assert list(tmp_path.iterdir()) == []  # nothing saved


def test_fetch_still_saves_direct_200(monkeypatch, tmp_path):
    _fake_transport(monkeypatch, {fetch.BOARD_URL: (200, None, b'{"jobs": []}')})
    path = fetch.fetch_board("t", raw_dir=tmp_path)
    assert path.read_bytes() == b'{"jobs": []}'
