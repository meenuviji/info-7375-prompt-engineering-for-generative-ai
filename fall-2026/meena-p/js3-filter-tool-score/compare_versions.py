"""Compare FILTER.md v1 and v2 against my blind verdicts on set B (held-out) ONLY.

Usage: .venv/bin/python compare_versions.py
Reads labels/set_B_labels.csv, output/filter_results.csv (v1), output/filter_results_v2.csv (v2).
Writes audit/RULE_CHANGE_v2.md and prints it. Computed numbers only; no interpretation.

Per version, over set B rows with a y/n verdict ("?" excluded from every count but reported):
- agree:              filter KEPT & y, or filter REJECTED & n
- kept but I said n:  filter KEPT & n
- rejected but I said y: filter REJECTED & y
- filter CANNOT_TELL with my y/n: reported separately (neither agree nor error)
"""

import csv

from src import config as cfg

RESULTS = {"v1": cfg.RESULTS_CSV, "v2": "output/filter_results_v2.csv"}
REPORT = "audit/RULE_CHANGE_v2.md"
CHANGE = 'Removed "associate" from R5 (role rules, title only). Everything else as v1.'


def read_csv(rel):
    with open(cfg.PROJECT_ROOT / rel, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def score_version(labels, results) -> dict:
    c = {"rows": len(labels), "question": 0, "judged": 0, "agree": 0, "kept_n": 0, "rejected_y": 0,
         "cannot_tell": 0}
    for lab in labels:
        verdict = lab["my_verdict"].strip()
        if verdict not in {"y", "n", "?"}:
            raise ValueError(f"{lab['provider']}/{lab['id']}: verdict {verdict!r}; label every row first")
        if verdict == "?":
            c["question"] += 1
            continue
        c["judged"] += 1
        decision = results[(lab["provider"], lab["id"])]["decision"]
        if decision == cfg.CANNOT_TELL:
            c["cannot_tell"] += 1
        elif (decision, verdict) in {(cfg.KEPT, "y"), (cfg.REJECTED, "n")}:
            c["agree"] += 1
        elif decision == cfg.KEPT:
            c["kept_n"] += 1
        else:
            c["rejected_y"] += 1
    return c


def result_cell(stats: dict) -> str:
    v1, v2 = stats["v1"], stats["v2"]
    return (f"Set B (n={v1['rows']}, \"?\" {v1['question']} excluded): "
            f"v1 agree {v1['agree']}/{v1['judged']}, kept-but-n {v1['kept_n']}, rejected-but-y {v1['rejected_y']}; "
            f"v2 agree {v2['agree']}/{v2['judged']}, kept-but-n {v2['kept_n']}, rejected-but-y {v2['rejected_y']}")


def build() -> tuple[str, dict]:
    labels = read_csv("labels/set_B_labels.csv")
    results = {v: {(r["provider"], r["id"]): r for r in read_csv(p)} for v, p in RESULTS.items()}
    stats = {v: score_version(labels, results[v]) for v in RESULTS}

    whole = {v: {d: sum(r["decision"] == d for r in results[v].values()) for d in cfg.DECISIONS} for v in RESULTS}
    changed = [(k, results["v1"][k], results["v2"][k]) for k in results["v1"]
               if results["v1"][k]["decision"] != results["v2"][k]["decision"]]
    in_b = {(r["provider"], r["id"]) for r in labels}
    verdicts = {(r["provider"], r["id"]): r["my_verdict"].strip() for r in labels}

    L = ["# Rule change v1 -> v2: set B comparison", "",
         "**Computed by compare_versions.py; interpretation to be written by me.**", "",
         f"Change: {CHANGE}", "",
         f"Measured on: set B held-out only ({stats['v1']['rows']} postings, labeled blind; "
         "set A was not used for these numbers).", "",
         "| Version | Judged (y/n) | Agree | Filter KEPT, I said n | Filter REJECTED, I said y | Filter CANNOT_TELL | My \"?\" (excluded) |",
         "|---|---|---|---|---|---|---|"]
    for v in RESULTS:
        s = stats[v]
        L.append(f"| {v} | {s['judged']} | {s['agree']} | {s['kept_n']} | {s['rejected_y']} | "
                 f"{s['cannot_tell']} | {s['question']} |")
    yes = sum(verdict == "y" for verdict in verdicts.values())
    L += ["", f"My set B verdicts: y {yes}, n {sum(v == 'n' for v in verdicts.values())}, "
          f"? {sum(v == '?' for v in verdicts.values())}.", "",
          "## Whole snapshot (context only, not labeled; not a measure of correctness)", "",
          "| Version | KEPT | REJECTED | CANNOT_TELL |", "|---|---|---|---|"]
    for v in RESULTS:
        L.append(f"| {v} | {whole[v][cfg.KEPT]} | {whole[v][cfg.REJECTED]} | {whole[v][cfg.CANNOT_TELL]} |")
    L += ["", f"Postings whose decision changed between v1 and v2: {len(changed)}", ""]
    if changed:
        L += ["| Title | v1 | v2 | v1 rules | v2 rules | In set B | My verdict |", "|---|---|---|---|---|---|---|"]
        for k, a, b in sorted(changed, key=lambda x: x[0]):
            L.append(f"| {a['title'].replace('|', chr(92) + '|')} | {a['decision']} ({a['score']}) | "
                     f"{b['decision']} ({b['score']}) | {a['rules_fired']} | {b['rules_fired']} | "
                     f"{'yes' if k in in_b else 'no'} | {verdicts.get(k, '—')} |")
    L += ["", "## Change-log Result cell", "", result_cell(stats), "",
          "## Interpretation", "", "_To be written by me._", ""]
    return "\n".join(L), stats


def main() -> int:
    report, _ = build()
    out = cfg.PROJECT_ROOT / REPORT
    out.parent.mkdir(exist_ok=True)
    out.write_text(report, encoding="utf-8")
    print(report)
    print(f"\nwrote {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
