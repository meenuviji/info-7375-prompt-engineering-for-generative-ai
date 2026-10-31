"""Standalone checks for verdict output (CONTRACT.md wrong versions 1 and 2).

The rule judge is not built in this layer; these run against any list of verdicts
shaped like CONTRACT.md "Out".
"""

import re

from agent.persona import get_path

# Segments are keys or list indexes (e.g. resume.experience.0.title); each is checked by get_path.
CITATION_RE = re.compile(r"\b(resume|posting)((?:\.(?:[A-Za-z_][A-Za-z0-9_]*|\d+))+)")
JUSTIFICATION_KEYS = ("rule_justification", "claude_justification")


def citations(text: str) -> list[str]:
    return [m.group(1) + m.group(2) for m in CITATION_RE.finditer(text)]


def validate_justification(text: str, resume: dict, posting: dict) -> list[str]:
    """Return errors; empty list means valid.

    Valid = names >=1 resume.* and >=1 posting.* key path, and every named path exists.
    """
    errors = []
    cited = citations(text)
    if not any(c.startswith("resume.") for c in cited):
        errors.append("no resume field cited")
    if not any(c.startswith("posting.") for c in cited):
        errors.append("no posting field cited")
    roots = {"resume": resume, "posting": posting}
    for c in cited:
        root, _, path = c.partition(".")
        try:
            get_path(roots[root], path)
        except KeyError:
            errors.append(f"cited field does not exist: {c}")
    return errors


def check_alignment(verdicts: list[dict], postings: list[dict]) -> list[str]:
    """Every justification must quote the title of the posting with its own posting_id."""
    by_id = {p["id"]: p for p in postings}
    errors = []
    for v in verdicts:
        pid = v["posting_id"]
        if pid not in by_id:
            errors.append(f"{pid}: posting_id not in postings")
            continue
        quoted = f'"{by_id[pid]["title"]}"'
        for key in JUSTIFICATION_KEYS:
            if key in v and quoted not in v[key]:
                errors.append(f"{pid}: {key} does not quote its own title {quoted}")
    return errors
