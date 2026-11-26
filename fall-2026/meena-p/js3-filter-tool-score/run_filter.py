"""Apply the FILTER.md filter to every posting in data/raw/.

Usage: .venv/bin/python run_filter.py [--version v1|v2]
v1 (default) writes output/filter_results.csv (the file set A/B were sampled from);
v2 writes output/filter_results_v2.csv. Prints counts per decision.
"""

import argparse
import csv
from collections import Counter

from src import config as cfg
from src.filter import VERSIONS, evaluate
from src.postings import load_postings

OUTPUTS = {"v1": cfg.RESULTS_CSV, "v2": "output/filter_results_v2.csv"}

COLUMNS = ["provider", "board", "id", "title", "decision", "score", "rules_fired", "close_call"]


def filter_rows(postings, version: str = "v1") -> list[dict]:
    rows = []
    for p in postings:
        r = evaluate(p.title, p.description, version)
        rows.append({
            "provider": p.provider, "board": p.board, "id": p.id, "title": p.title,
            "decision": r.decision, "score": r.score,
            "rules_fired": ";".join(r.rules_fired), "close_call": str(r.close_call).lower(),
        })
    return rows


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--version", choices=VERSIONS, default="v1")
    args = parser.parse_args(argv)

    postings, report = load_postings()
    rows = filter_rows(postings, args.version)

    print(f"filter version: FILTER.md {args.version}")
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
    print(f"close calls  {sum(r['close_call'] == 'true' for r in rows)} "
          f"(score in {sorted(cfg.CLOSE_CALL_SCORES)}, no exclusion, description present)")
    print(f"wrote {out.relative_to(cfg.PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
