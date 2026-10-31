"""Seen-id state. New postings are identified by Greenhouse `id`, never by title."""

import json
from pathlib import Path

STATE_PATH = Path("state/seen_ids.json")


def posting_ids(board: dict) -> list[int]:
    return [job["id"] for job in board["jobs"]]


def load_seen(path: Path = STATE_PATH) -> set[int] | None:
    """Return the previous run's ids, or None if there is no state (baseline run)."""
    if not path.exists():
        return None
    return set(json.loads(path.read_text())["seen_ids"])


def save_seen(ids, path: Path = STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"seen_ids": sorted(ids)}, indent=2) + "\n")


def new_ids(current: list[int], seen: set[int] | None) -> list[int]:
    """Ids in current that are not in seen. A baseline (seen is None) reports none."""
    if seen is None:
        return []
    return sorted(set(current) - seen)
