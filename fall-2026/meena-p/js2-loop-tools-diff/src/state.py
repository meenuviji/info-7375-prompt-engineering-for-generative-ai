"""Per-board state for JS2. Base: the_contract_watch agent/state.py (JS1).

Kept from JS1: postings are identified by `id`, never by title, and the stored ids
are REPLACED by the board's current ids on every verified observation. They are
never merged with earlier ids.

Changed for JS2 (GATE.md 5.1, clarification 4):
- One file per board at output/states/<board_token>.json.
- The file holds active_job_ids plus a run ledger. Each processed board appends one
  ledger entry. A failed board appends its error and leaves active_job_ids unchanged.
- Boards the run never reaches (or is interrupted on) are not written at all.
- An unreadable or corrupt state file raises StateError, which stops the run.
"""

import json
from pathlib import Path

from . import config as cfg

SCHEMA_VERSION = 1


class StateError(Exception):
    """Loop-level: a state file cannot be read or is corrupt."""


def _is_id(value) -> bool:
    return (isinstance(value, int) and not isinstance(value, bool)) or (isinstance(value, str) and value != "")


def sort_ids(ids) -> list:
    # Greenhouse ids are ints and Lever ids are strings; the key keeps a mixed set sortable.
    return sorted(set(ids), key=lambda v: (isinstance(v, str), v))


def state_path(root: Path, token: str) -> Path:
    return Path(root) / cfg.STATES_DIR / f"{token}.json"


def load_state(io, path: Path) -> dict | None:
    """The board's previous state, or None if the board has no state file yet."""
    if not io.exists(path):
        return None
    try:
        data = json.loads(io.read_bytes(path))
    except OSError as e:
        raise StateError(f"cannot read state file {path}: {e}") from e
    except (ValueError, RecursionError) as e:
        raise StateError(f"state file {path} is not valid JSON: {e}") from e
    if not isinstance(data, dict):
        raise StateError(f"state file {path}: root must be an object")
    if not isinstance(data.get("board_token"), str) or not isinstance(data.get("provider"), str):
        raise StateError(f"state file {path}: board_token and provider must be strings")
    ids = data.get("active_job_ids", "missing")
    if ids is not None and not (isinstance(ids, list) and all(_is_id(v) for v in ids)):
        raise StateError(f"state file {path}: active_job_ids must be a list of ids or null")
    if not isinstance(data.get("ledger"), list):
        raise StateError(f"state file {path}: ledger must be a list")
    return data


def diff_ids(prior: list | None, current: list) -> dict | None:
    """Added / removed / unchanged against the previous ids. None means a baseline (no previous ids)."""
    if prior is None:
        return None
    p, c = set(prior), set(current)
    return {"added": sort_ids(c - p), "removed": sort_ids(p - c), "unchanged": len(p & c)}


def next_state(prior_state: dict | None, *, token: str, provider: str, entry: dict,
               current_ids: list | None) -> dict:
    """The new state. current_ids is None for a failed board, which keeps its earlier ids."""
    ledger = list(prior_state["ledger"]) if prior_state else []
    ledger.append(entry)
    if current_ids is not None:
        active = sort_ids(current_ids)  # replace, never merge
    else:
        active = prior_state["active_job_ids"] if prior_state else None
    return {
        "schema_version": SCHEMA_VERSION,
        "board_token": token,
        "provider": provider,
        "active_job_ids": active,
        "ledger": ledger,
    }


def save_state(io, path: Path, state: dict) -> None:
    io.make_dirs(path.parent)
    io.replace_atomic(path, (json.dumps(state, indent=2) + "\n").encode("utf-8"))
