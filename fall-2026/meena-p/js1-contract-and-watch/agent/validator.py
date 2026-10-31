"""Strict validator for Claude judge output. Rejects; never coerces or repairs."""

import json

from agent.persona import get_path
from agent.validate import citations

REQUIRED_KEYS = {"posting_id", "verdict", "resume_fields", "posting_fields", "justification"}
VERDICTS = ("relevant", "not_relevant")


def _no_duplicate_keys(pairs):
    keys = [k for k, _ in pairs]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate keys")
    return dict(pairs)


def validate_claude_output(raw: str, posting: dict, persona: dict) -> tuple[dict | None, list[str]]:
    """Return (parsed, errors). parsed is None unless errors is empty."""
    try:
        obj = json.loads(raw, object_pairs_hook=_no_duplicate_keys)
    except (ValueError, TypeError) as e:
        return None, [f"not JSON: {e}"]
    if not isinstance(obj, dict):
        return None, ["not a JSON object"]

    errors = []
    keys = set(obj)
    if keys - REQUIRED_KEYS:
        errors.append(f"extra keys: {sorted(keys - REQUIRED_KEYS)}")
    if REQUIRED_KEYS - keys:
        errors.append(f"missing keys: {sorted(REQUIRED_KEYS - keys)}")
        return None, errors

    if not isinstance(obj["posting_id"], str):
        errors.append("posting_id is not a string")
    elif obj["posting_id"] != str(posting["id"]):
        errors.append(f"posting_id {obj['posting_id']!r} does not match posting sent {posting['id']}")

    if obj["verdict"] not in VERDICTS:
        errors.append(f"verdict not one of {VERDICTS}: {obj['verdict']!r}")

    if not isinstance(obj["justification"], str) or not obj["justification"].strip():
        errors.append("justification is not a non-empty string")

    roots = {"resume": persona, "posting": posting}
    cited = []
    for key, prefix in (("resume_fields", "resume"), ("posting_fields", "posting")):
        fields = obj[key]
        if not isinstance(fields, list) or not fields:
            errors.append(f"{key} is not a non-empty list")
            continue
        for f in fields:
            if not isinstance(f, str) or not f.startswith(prefix + "."):
                errors.append(f"{key} entry is not a '{prefix}.' path: {f!r}")
            else:
                cited.append(f)
    if isinstance(obj["justification"], str):
        cited += citations(obj["justification"])

    for c in dict.fromkeys(cited):
        root, _, path = c.partition(".")
        try:
            get_path(roots[root], path)
        except KeyError:
            errors.append(f"cited field does not exist: {c}")

    return (None, errors) if errors else (obj, [])
