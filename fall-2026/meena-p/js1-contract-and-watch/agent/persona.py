"""Load and validate the fictional persona. The agent refuses to run on anything else."""

import json
import re
from pathlib import Path

PERSONA_PATH = Path("resume/persona.json")
REQUIRED_FIELDS = ("personal.location", "skills")  # CONTRACT.md "In"
EMAIL_RE = re.compile(r"[^\s@]+@[^\s@]+\.[^\s@]+")


class PersonaError(Exception):
    pass


def get_path(obj, dotted: str):
    """Resolve a dotted key path (list items by index, e.g. experience.0.title);
    raise KeyError if any segment is missing."""
    for key in dotted.split("."):
        if isinstance(obj, dict) and key in obj:
            obj = obj[key]
        elif isinstance(obj, list) and key.isdigit() and int(key) < len(obj):
            obj = obj[int(key)]
        else:
            raise KeyError(dotted)
    return obj


def _walk(obj, key=None):
    """Yield (key, string_value) for every string in obj, with its nearest dict key."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _walk(v, k)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk(v, key)
    elif isinstance(obj, str):
        yield key, obj


def _is_555(phone: str) -> bool:
    digits = re.sub(r"\D", "", phone)
    return len(digits) >= 7 and digits[-7:-4] == "555"


def validate_persona(persona: dict) -> None:
    errors = []
    for field in REQUIRED_FIELDS:
        try:
            value = get_path(persona, field)
        except KeyError:
            errors.append(f"missing required field: {field}")
            continue
        if value in (None, "", [], {}):
            errors.append(f"empty required field: {field}")
    for key, value in _walk(persona):
        for email in EMAIL_RE.findall(value):
            if not email.lower().endswith("@example.com"):
                errors.append(f"email not @example.com: field {key!r}")
        if key and "phone" in key.lower() and not _is_555(value):
            errors.append(f"phone does not use 555: field {key!r}")
    if errors:
        # Report field names only, never values: do not print résumé contents.
        raise PersonaError("refusing to run: " + "; ".join(errors))


def load_persona(path: Path = PERSONA_PATH) -> dict:
    persona = json.loads(path.read_text())
    validate_persona(persona)
    return persona
