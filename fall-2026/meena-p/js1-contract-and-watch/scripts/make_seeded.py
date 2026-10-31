"""Construct evidence/raw/SEEDED_earlier.json from a saved live response.

SEEDED: removes exactly the 5 postings with the largest ids (sorted numerically).
Everything else, including `meta`, is left as in the live response.
Usage: python scripts/make_seeded.py <live_raw.json> [out_path]
"""

import json
import sys
from pathlib import Path

N_REMOVED = 5


def make_seeded(board: dict, n: int = N_REMOVED) -> tuple[dict, list[int]]:
    removed = sorted(j["id"] for j in board["jobs"])[-n:]
    seeded = dict(board)
    seeded["jobs"] = [j for j in board["jobs"] if j["id"] not in set(removed)]
    return seeded, removed


if __name__ == "__main__":
    src = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("evidence/raw/SEEDED_earlier.json")
    board = json.loads(src.read_text())
    seeded, removed = make_seeded(board)
    out.write_text(json.dumps(seeded, indent=2, ensure_ascii=False) + "\n")
    print(f"source={src} jobs_in={len(board['jobs'])} jobs_out={len(seeded['jobs'])}")
    print("removed_ids=" + ",".join(map(str, removed)))
    print(f"wrote {out}")
