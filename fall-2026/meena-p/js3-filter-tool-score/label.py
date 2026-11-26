"""Blind labeling tool.

Usage: .venv/bin/python label.py labels/set_A_labels.csv

For each row with a blank verdict: clears the screen and shows title, board, location and
the first 800 characters of the description. It never shows (or computes) the filter
decision, score, or rules. Keys:
  y  relevant to the persona        n  not relevant        ?  cannot tell from the text
  f  show the full description, then ask again             q  save and quit
After y/n/? it asks for an optional one-line reason. The file is saved after every answer.
"""

import csv
import os
import sys
from pathlib import Path

from src.postings import load_postings

PREVIEW_CHARS = 800
VERDICTS = {"y": "y", "n": "n", "?": "?"}
COLUMNS = ["id", "provider", "my_verdict", "my_reason"]
PERSONA = ("Persona: Jordan Lee, entry-level / new-grad Data Engineer, Data Scientist, BI Analyst, "
           "or AI/ML Engineer; individual contributor; US or remote.")


def read_rows(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != COLUMNS:
            raise ValueError(f"{path}: expected columns {COLUMNS}, got {reader.fieldnames}")
        return list(reader)


def save_rows(path: Path, rows: list[dict]) -> None:
    tmp = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def render(posting, position: str, full: bool = False) -> str:
    desc = posting.description or "(no description text)"
    if not full and len(desc) > PREVIEW_CHARS:
        desc = desc[:PREVIEW_CHARS] + f"\n... [{len(posting.description) - PREVIEW_CHARS} more characters; press f]"
    return (f"{position}   {PERSONA}\n\n"
            f"TITLE:    {posting.title}\n"
            f"BOARD:    {posting.board}\n"
            f"LOCATION: {posting.location}\n"
            f"{'-' * 72}\n{desc}\n{'-' * 72}\n")


def label_file(path: Path, postings_by_key: dict, ask=input, show=print, clear=None) -> str:
    """Label every blank row. Returns "done" or "quit". ask/show/clear are injectable for tests."""
    clear = clear or (lambda: show("\033[2J\033[H", end=""))
    rows = read_rows(path)
    todo = [r for r in rows if not r["my_verdict"].strip()]
    total = len(rows)
    for row in todo:
        posting = postings_by_key.get((row["provider"], row["id"]))
        if posting is None:
            raise KeyError(f"posting {row['provider']}/{row['id']} not found in data/raw/")
        done = sum(1 for r in rows if r["my_verdict"].strip())
        full = False
        while True:
            clear()
            show(render(posting, f"[{done + 1}/{total}]", full))
            key = ask("y relevant / n not relevant / ? cannot tell / f full text / q quit: ").strip().lower()
            if key == "q":
                save_rows(path, rows)
                return "quit"
            if key == "f":
                full = True
                continue
            if key in VERDICTS:
                row["my_verdict"] = VERDICTS[key]
                row["my_reason"] = " ".join(ask("optional one-line reason (Enter to skip): ").split())
                save_rows(path, rows)
                break
            show(f"unrecognised key {key!r}")
    return "done"


def main(argv) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    path = Path(argv[1])
    postings, _ = load_postings()
    by_key = {(p.provider, p.id): p for p in postings}
    try:
        outcome = label_file(path, by_key)
    except (KeyboardInterrupt, EOFError):
        print("\nstopped; every answer given so far is saved")
        return 1
    rows = read_rows(path)
    print(f"{outcome}: {sum(1 for r in rows if r['my_verdict'].strip())}/{len(rows)} labeled in {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
