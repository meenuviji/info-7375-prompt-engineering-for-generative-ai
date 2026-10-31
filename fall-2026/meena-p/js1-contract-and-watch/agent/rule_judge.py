"""CONTRACT.md "The rule", applied literally and deterministically. No model. Output kind=RECORD.

Clause 1 is case-insensitive (the contract says so). Clauses 2 and 3 do not say so and are
applied as written: case-sensitive substring match.
"""

TITLE_KEYWORDS = ("AI Engineer", "ML Engineer", "Machine Learning", "Data Engineer")
SENIORITY_WORDS = ("Senior", "Sr.", "Staff", "Principal", "Lead", "Director", "Head", "Manager")


def persona_city(persona: dict) -> str:
    """City in resume.personal.location ("Boston, MA" -> "Boston")."""
    return persona["personal"]["location"].split(",")[0].strip()


def judge(posting: dict, persona: dict) -> dict:
    title = posting["title"]
    loc = (posting.get("location") or {}).get("name") or ""
    city = persona_city(persona)

    hits = [k for k in TITLE_KEYWORDS if k.lower() in title.lower()]
    c1 = bool(hits)
    c2_match = [w for w in (city, "Remote") if w in loc]
    c2 = bool(c2_match)
    senior = [w for w in SENIORITY_WORDS if w in title]
    c3 = not senior

    kw = ", ".join(f'"{k}"' for k in TITLE_KEYWORDS)
    parts = [
        f'Clause 1 {"PASSED" if c1 else "FAILED"}: `posting.title` "{title}" '
        + (f'contains {", ".join(repr(h) for h in hits)}' if c1 else f"contains none of {kw}"),
        f'Clause 2 {"PASSED" if c2 else "FAILED"}: `posting.location.name` "{loc}" '
        + (f'contains "{c2_match[0]}"' if c2 else f'contains neither "{city}" nor "Remote"')
        + f' (city "{city}" from `resume.personal.location`)',
        f'Clause 3 {"PASSED" if c3 else "FAILED"}: `posting.title` '
        + (f'contains {", ".join(repr(s) for s in senior)}' if senior
           else "contains no seniority word"),
    ]
    relevant = c1 and c2 and c3
    if relevant:
        head = "RELEVANT: all three clauses passed."
    else:
        failed = [str(i) for i, ok in enumerate((c1, c2, c3), 1) if not ok]
        head = f"NOT RELEVANT: clause {', '.join(failed)} failed."
    return {
        "posting_id": posting["id"],
        "verdict": "relevant" if relevant else "not_relevant",
        "justification": head + " " + "; ".join(parts) + ".",
        "cited_resume_fields": ["resume.personal.location"],
        "cited_posting_fields": ["posting.title", "posting.location.name"],
        "kind": "RECORD",
    }
