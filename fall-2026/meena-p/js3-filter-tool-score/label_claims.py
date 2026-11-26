"""Label shortlist claims against FILTER.md section 2 evidence rules.

Usage: .venv/bin/python label_claims.py shortlist/claims.csv

For each row with a blank my_label: clears the screen and shows the posting title, the claim
and the quoted sentence. It does not show agent_answer or any filter decision, score or rules.
Keys:
  s  supported      c  contradicted      i  insufficient
  f  show the full description, then ask again                q  save and quit
After s/c/i it asks for an optional one-line reason. The file is saved after every answer.
"""

import csv
import os
import sys
from pathlib import Path

from src.postings import load_postings

COLUMNS = ["posting_id", "title", "claim_id", "claim", "quoted_sentence", "agent_answer", "my_label", "my_reason"]
LABELS = {"s": "supported", "c": "contradicted", "i": "insufficient"}
RULES = ("s = a quoted sentence states the claim in equivalent terms;  "
         "c = the posting states the opposite;  i = nothing directly establishes it")


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


def render(row: dict, description: str | None, position: str) -> str:
    text = (f"{position}   {RULES}\n\n"
            f"POSTING:  {row['title']} ({row['posting_id']})\n"
            f"CLAIM:    {row['claim']}\n\n"
            f"QUOTED SENTENCE:\n  {row['quoted_sentence']}\n")
    if description is not None:
        text += f"{'-' * 72}\nFULL DESCRIPTION:\n{description or '(no description text)'}\n{'-' * 72}\n"
    return text


def label_file(path: Path, descriptions: dict, ask=input, show=print, clear=None) -> str:
    """Label every row with a blank my_label. Returns "done" or "quit"."""
    clear = clear or (lambda: show("\033[2J\033[H", end=""))
    rows = read_rows(path)
    total = len(rows)
    for row in [r for r in rows if not r["my_label"].strip()]:
        if row["posting_id"] not in descriptions:
            raise KeyError(f"posting {row['posting_id']} not found in data/raw/")
        done = sum(1 for r in rows if r["my_label"].strip())
        full = None
        while True:
            clear()
            show(render(row, full, f"[{done + 1}/{total}] {row['claim_id']}"))
            key = ask("s supported / c contradicted / i insufficient / f full text / q quit: ").strip().lower()
            if key == "q":
                save_rows(path, rows)
                return "quit"
            if key == "f":
                full = descriptions[row["posting_id"]]
                continue
            if key in LABELS:
                row["my_label"] = LABELS[key]
                row["my_reason"] = " ".join(ask("optional one-line reason (Enter to skip): ").split())
                save_rows(path, rows)
                break
            show(f"unrecognised key {key!r}")
    return "done"


def descriptions_by_id() -> dict:
    by_id: dict[str, str] = {}
    for p in load_postings()[0]:
        if p.id in by_id:
            raise ValueError(f"posting id {p.id} occurs under two providers; claims.csv cannot tell them apart")
        by_id[p.id] = p.description
    return by_id


def main(argv) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    path = Path(argv[1])
    try:
        outcome = label_file(path, descriptions_by_id())
    except (KeyboardInterrupt, EOFError):
        print("\nstopped; every answer given so far is saved")
        return 1
    rows = read_rows(path)
    print(f"{outcome}: {sum(1 for r in rows if r['my_label'].strip())}/{len(rows)} labeled in {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
