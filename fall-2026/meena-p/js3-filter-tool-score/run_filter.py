"""Apply the FILTER.md filter to every posting in data/raw/.

Usage: .venv/bin/python run_filter.py [--version v1|v2]
v1 (default) writes output/filter_results.csv (the file set A/B were sampled from);
v2 writes output/filter_results_v2.csv. Prints counts per decision.
"""

import argparse
import csv
from collections import Counter

from src import config as cfg
from src import filter_v3
from src import location as loc
from src.filter import VERSIONS, evaluate
from src.postings import load_postings

OUTPUTS = {"v1": cfg.RESULTS_CSV, "v2": "output/filter_results_v2.csv", "v3": "output/filter_results_v3.csv"}
ALL_VERSIONS = (*VERSIONS, "v3")  # v3 = FILTER.md as committed in 4923b21 (src/filter_v3.py)

COLUMNS = ["provider", "board", "id", "title", "decision", "score", "rules_fired", "close_call"]


def filter_rows(postings, version: str = "v1") -> list[dict]:
    rows = []
    for p in postings:
        if version == "v3":
            r = filter_v3.evaluate(p.title, p.location, p.description)
        else:
            r = evaluate(p.title, p.description, version)
        rows.append({
            "provider": p.provider, "board": p.board, "id": p.id, "title": p.title,
            "decision": r.decision, "score": r.score,
            "rules_fired": ";".join(r.rules_fired), "close_call": str(r.close_call).lower(),
        })
    return rows


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--version", choices=ALL_VERSIONS, default="v1")
    args = parser.parse_args(argv)

    postings, report = load_postings(keep_missing_title=args.version == "v3")
    rows = filter_rows(postings, args.version)

    print("rule set: v3 = FILTER.md as committed in 4923b21 (header says v1)" if args.version == "v3"
          else f"rule set: {args.version} (original FILTER.md v1 contract; src/filter.py)")
    out = cfg.PROJECT_ROOT / OUTPUTS[args.version]
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"postings loaded: {report.loaded} "
          f"(skipped, no title: {report.skipped_no_title}; duplicates dropped: {report.duplicates_dropped})")
    counts = Counter(r["decision"] for r in rows)
    for decision in cfg.DECISIONS:
        print(f"{decision:12} {counts.get(decision, 0)}")
    if args.version == "v3":
        print(f"close calls  {sum(r['close_call'] == 'true' for r in rows)} "
              "(no exclusion and score 4, or score >= 5 rejected only by X3 or X5)")
        classes = Counter()
        non_us = Counter()
        for p in postings:
            c, text = loc.classify(p.location, p.description)
            classes[c] += 1
            if c == loc.NON_US:
                non_us[text] += 1
        print(f"location: {dict(classes)}")
        print("location strings classified NON_US (check for missed US places):")
        for text, n in sorted(non_us.items(), key=lambda x: (-x[1], x[0])):
            print(f"  {n:4}  {text}")
    else:
        print(f"close calls  {sum(r['close_call'] == 'true' for r in rows)} "
              f"(score in {sorted(cfg.CLOSE_CALL_SCORES)}, no exclusion, description present)")
    print(f"wrote {out.relative_to(cfg.PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
