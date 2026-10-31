"""Build labels/postings_20.csv from the saved live response. Runs no judge.

Selection (decided before any judge ran on these postings), seed 7375:
1. clause1_pass: every posting whose title passes CONTRACT.md rule clause 1, up to 8
   (seeded sample from id-sorted pool if more than 8).
2. data_adjacent: titles matching Data/Analytics/Analyst/AI/ML/Machine Learning/Scientist
   (whole word, case-insensitive) that fail clause 1, filling groups 1+2 up to 10.
3. other: the remaining rows to reach 20, seeded sample of everything else.
Split: 10 dev / 10 heldout, seeded, alternating within each id-sorted, shuffled group so
every group is spread across both splits.
Prints counts only, never rows.
Usage: python scripts/make_labeling_sheet.py <live_raw.json> [out.csv]
"""

import csv
import html
import random
import re
import sys
from collections import Counter
from pathlib import Path
import json

from agent.rule_judge import SENIORITY_WORDS, TITLE_KEYWORDS

SEED = 7375
TOTAL, GROUPS_1_2, MAX_CLAUSE1 = 20, 10, 8
EXCERPT_CHARS = 400
ADJACENT = re.compile(r"\b(?:Data|Analytics|Analysts?|AI|ML|Machine Learning|Scientists?)\b",
                      re.IGNORECASE)
INTRO_DIV = re.compile(r'<div class="content-intro">.*?</div>', re.S)
COLUMNS = ["posting_id", "selection_group", "split", "title", "location",
           "seniority_words_in_title", "requirements_excerpt", "my_label", "notes"]


def passes_clause1(title: str) -> bool:
    return any(k.lower() in title.lower() for k in TITLE_KEYWORDS)


def excerpt(content: str | None) -> str:
    """Plain text after dropping the Cloudflare boilerplate intro div, first 400 chars."""
    h = INTRO_DIV.sub("", html.unescape(content or ""), count=1)
    text = re.sub(r"<[^>]+>", " ", h)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()[:EXCERPT_CHARS]


def select(jobs: list[dict]) -> dict[str, list[dict]]:
    rng = random.Random(SEED)
    by_id = sorted(jobs, key=lambda j: j["id"])
    c1 = [j for j in by_id if passes_clause1(j["title"])]
    if len(c1) > MAX_CLAUSE1:
        c1 = sorted(rng.sample(c1, MAX_CLAUSE1), key=lambda j: j["id"])
    taken = {j["id"] for j in c1}
    adj_pool = [j for j in by_id if j["id"] not in taken and not passes_clause1(j["title"])
                and ADJACENT.search(j["title"])]
    adj = sorted(rng.sample(adj_pool, min(GROUPS_1_2 - len(c1), len(adj_pool))),
                 key=lambda j: j["id"])
    taken |= {j["id"] for j in adj}
    other_pool = [j for j in by_id if j["id"] not in taken]
    other = sorted(rng.sample(other_pool, TOTAL - len(taken)), key=lambda j: j["id"])
    return {"clause1_pass": c1, "data_adjacent": adj, "other": other}


def assign_splits(groups: dict[str, list[dict]]) -> dict[int, str]:
    rng = random.Random(SEED)
    split, toggle = {}, 0
    for name in ("clause1_pass", "data_adjacent", "other"):
        ids = [j["id"] for j in groups[name]]
        rng.shuffle(ids)
        for i in ids:
            split[i] = ("dev", "heldout")[toggle]
            toggle ^= 1
    return split


def main(src: Path, out: Path) -> None:
    jobs = json.loads(src.read_text())["jobs"]
    groups = select(jobs)
    split = assign_splits(groups)
    rows = []
    for name, js in groups.items():
        for j in js:
            rows.append({
                "posting_id": j["id"],
                "selection_group": name,
                "split": split[j["id"]],
                "title": j["title"],
                "location": (j.get("location") or {}).get("name", ""),
                "seniority_words_in_title": "; ".join(w for w in SENIORITY_WORDS
                                                      if w in j["title"]),
                "requirements_excerpt": excerpt(j.get("content")),
                "my_label": "",
                "notes": "",
            })
    # dev rows first, heldout rows last, so heldout can stay out of view while labeling dev.
    order = {"dev": 0, "heldout": 1}
    rows.sort(key=lambda r: (order[r["split"]], r["selection_group"], r["posting_id"]))

    assert len(rows) == TOTAL and len({r["posting_id"] for r in rows}) == TOTAL
    assert Counter(r["split"] for r in rows) == {"dev": 10, "heldout": 10}
    for name in groups:
        assert {r["split"] for r in rows if r["selection_group"] == name} == {"dev", "heldout"}
    assert all(r["my_label"] == "" and r["notes"] == "" for r in rows)
    assert all(r["requirements_excerpt"] for r in rows)

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    print(f"source={src} postings={len(jobs)} seed={SEED} wrote {out}")
    for (g, s), n in sorted(Counter((r["selection_group"], r["split"]) for r in rows).items()):
        print(f"  {g:14s} {s:8s} {n}")


if __name__ == "__main__":
    main(Path(sys.argv[1]),
         Path(sys.argv[2]) if len(sys.argv) > 2 else Path("labels/postings_20.csv"))
