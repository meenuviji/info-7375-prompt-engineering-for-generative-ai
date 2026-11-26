"""Score report: what sets the numbers, and two one-object experiments on held-out set B.

Usage: .venv/bin/python score_report.py
Reads data/raw/ (through src/postings.py), labels/set_B_labels.csv and
output/filter_results_v2.csv (only to cross-check the baseline). Writes SCORE_REPORT_DRAFT.md
and prints it. Computed numbers only; no interpretation.

Baseline: filter file v2 (src/filter.py: v1 minus "associate" in R5), keep threshold 5.
- Change 1 (a setting): keep threshold 5 -> 4, filter file v2 unchanged.
- Change 2 (the filter file): v2 -> v1 (only difference: "associate" in R5), threshold 5.
  (v1 and v2 have identical topic rules; decision of 2026-11-25 to compare them as they are.)

Metrics on set B, verdicts y/n only ("?" excluded and counted):
- agree:          KEPT & y, or REJECTED & n
- false keep:     KEPT & n
- false reject:   REJECTED & y
- filter CANNOT_TELL with a y/n verdict: counted separately
"""

import csv
import re

from src import config as cfg
from src import location
from src.filter import evaluate
from src.postings import load_postings

REPORT = "SCORE_REPORT_DRAFT.md"
BASELINE_THRESHOLD = cfg.KEEP_THRESHOLD

EXPERIMENTS = [
    ("Baseline", "filter v2, threshold 5", "v2", BASELINE_THRESHOLD),
    ("Change 1 (setting)", "filter v2, threshold 4", "v2", BASELINE_THRESHOLD - 1),
    ("Change 2 (filter file)", "filter v1, threshold 5", "v1", BASELINE_THRESHOLD),
]


def inventory() -> list[tuple[str, str, str, str]]:
    """(item, value, where, origin). Values are read from the code, origins are stated by hand.
    No code in this project fits any parameter to labels; nothing is marked "fitted"."""
    prompt = cfg.PROJECT_ROOT / "prompts/justify_claims.md"
    filter_src = (cfg.PROJECT_ROOT / "src/filter.py").read_text()
    m = re.search(r'ROLE_RULES_V2 = .*"R5": (\[[^\]]*\])', filter_src)
    return [
        ("Role weight (v1/v2)", str(cfg.ROLE_SCORE), "src/config.py ROLE_SCORE",
         "hand-set: FILTER.md v1 as first committed (7b96757), section 1.4"),
        ("Topic weight (v1/v2)", str(cfg.TOPIC_POINT), "src/config.py TOPIC_POINT",
         "hand-set: FILTER.md v1 (7b96757)"),
        ("Topic cap (v1/v2)", str(cfg.TOPIC_CAP), "src/config.py TOPIC_CAP", "hand-set: FILTER.md v1 (7b96757)"),
        ("Keep threshold (v1/v2)", f">= {cfg.KEEP_THRESHOLD}", "src/config.py KEEP_THRESHOLD",
         "hand-set: FILTER.md v1 (7b96757); chosen over the build instructions' >= 4 on 2026-11-25"),
        ("Close-call band (v1/v2)", f"scores {sorted(cfg.CLOSE_CALL_SCORES)}", "src/config.py CLOSE_CALL_SCORES",
         "hand-set: FILTER.md v1 (7b96757)"),
        ("v2 rule change", f'R5 = {m.group(1) if m else "?"} ("associate" removed)', "src/filter.py ROLE_RULES_V2",
         "hand-set: chosen by me on 2026-11-25 after reading the set A audit; not fitted by code; "
         "the v2 diff was never applied to FILTER.md"),
        ("Weights / threshold (v3)",
         f"core role {cfg.V3_CORE_ROLE_POINTS}, R5 {cfg.V3_R5_POINT}, topic {cfg.V3_TOPIC_POINT}, no cap, "
         f"keep >= {cfg.V3_KEEP_THRESHOLD}, close call {cfg.V3_CLOSE_CALL_SCORE} or X3/X5-only",
         "src/config.py V3_*", "hand-set: FILTER.md as committed in 4923b21 (header says v1)"),
        ("US city list (v3 X3)", f"{len(location.US_CITIES)} cities", "src/location.py US_CITIES",
         "hand-set by Claude Code while implementing (judgment call, not in FILTER.md)"),
        ("Sampling seed", str(cfg.SEED), "src/config.py SEED",
         "hand-set: JS3 build instructions (2026-11-25), not FILTER.md"),
        ("Sample sizes", f"A: {cfg.SET_A_REJECTED} rejected + {cfg.SET_A_CLOSE_CALLS} close + "
         f"{cfg.SET_A_KEPT} kept (4 available); B: {cfg.SET_B_SIZE}", "src/config.py SET_*",
         "hand-set: JS3 build instructions (2026-11-25)"),
        ("Wilson z", "1.96", "audit.py Z", "inherited: statistics convention (two-sided 95% normal quantile)"),
        ("Rule of three", "3/n", "audit.py", "inherited: statistics convention (95% upper bound when 0 events)"),
        ("Label preview", "800 characters", "label.py PREVIEW_CHARS",
         "hand-set: JS3 build instructions (affects what I saw while labeling, not scoring)"),
        ("Claim prompt", f"{prompt.name} ({len(prompt.read_text().splitlines())} lines)", "prompts/justify_claims.md",
         "hand-written: my task text + FILTER.md section 2, with operating rules added by Claude Code"),
        ("Data snapshot", "3 boards, 1167 postings", "data/raw/, data/SOURCES_OF_DATA.md",
         "inherited: JS2 run 20261110T203921572430Z (boards from JS2's config)"),
    ]


def read_labels() -> list[dict]:
    with open(cfg.PROJECT_ROOT / "labels/set_B_labels.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        if r["my_verdict"].strip() not in {"y", "n", "?"}:
            raise ValueError(f"{r['provider']}/{r['id']}: verdict {r['my_verdict']!r}; label every row first")
    return rows


def decisions(postings, version: str, threshold: int) -> dict:
    return {(p.provider, p.id): evaluate(p.title, p.description, version, threshold) for p in postings}


def measure(labels, results) -> dict:
    m = {"n": len(labels), "question": 0, "judged": 0, "agree": 0, "false_keep": 0, "false_reject": 0,
         "cannot_tell": 0, "kept_B": 0}
    for lab in labels:
        verdict = lab["my_verdict"].strip()
        decision = results[(lab["provider"], lab["id"])].decision
        m["kept_B"] += decision == cfg.KEPT
        if verdict == "?":
            m["question"] += 1
            continue
        m["judged"] += 1
        if decision == cfg.CANNOT_TELL:
            m["cannot_tell"] += 1
        elif (decision, verdict) in {(cfg.KEPT, "y"), (cfg.REJECTED, "n")}:
            m["agree"] += 1
        elif decision == cfg.KEPT:
            m["false_keep"] += 1
        else:
            m["false_reject"] += 1
    m["kept_all"] = sum(r.decision == cfg.KEPT for r in results.values())
    return m


def baseline_matches_saved_csv(results) -> bool:
    with open(cfg.PROJECT_ROOT / "output/filter_results_v2.csv", newline="", encoding="utf-8") as f:
        saved = {(r["provider"], r["id"]): r["decision"] for r in csv.DictReader(f)}
    return saved == {k: r.decision for k, r in results.items()}


def pct(k: int, n: int) -> str:
    return f"{100 * k / n:.1f}%" if n else "n/a"


def signed(x: int) -> str:
    return f"{x:+d}"


def build() -> str:
    postings, _ = load_postings()
    labels = read_labels()
    titles = {(p.provider, p.id): p.title for p in postings}
    runs = {name: (desc, decisions(postings, v, t)) for name, desc, v, t in EXPERIMENTS}
    stats = {name: measure(labels, res) for name, (_, res) in runs.items()}
    base_name = EXPERIMENTS[0][0]
    base = stats[base_name]
    verdicts = [lab["my_verdict"].strip() for lab in labels]

    L = ["# Score report — DRAFT", "",
         "**Computed by score_report.py; interpretation to be written by me.**", "",
         "## 1. Numbers and prompts that affect scoring or the shortlist", "",
         "Origins: *hand-set* (a person chose it), *fitted* (code chose it from my labels) or "
         "*inherited* (from JS2 or a statistics convention). No code in this project fits a parameter, "
         "so nothing below is marked fitted.", "",
         "| Item | Value | Where | Origin |", "|---|---|---|---|"]
    for item, value, where, origin in inventory():
        L.append(f"| {item} | {value} | `{where}` | {origin} |")

    L += ["", "## 2. Experiments on held-out set B", "",
          f"Set B: {len(labels)} postings labeled blind. My verdicts: y {verdicts.count('y')}, "
          f"n {verdicts.count('n')}, ? {verdicts.count('?')} (\"?\" excluded from agree / false keep / "
          "false reject and counted separately).",
          f"Baseline recomputed from code matches `output/filter_results_v2.csv`: "
          f"{'yes' if baseline_matches_saved_csv(runs[base_name][1]) else 'NO'}.", "",
          "Each change alters one object only: Change 1 the keep threshold (a setting), Change 2 the "
          "filter file (v2 -> v1, whose only difference is \"associate\" in R5; the topic rules are "
          "identical in v1 and v2).", "",
          "| Run | Configuration | Judged | Agree | Agree % | False keeps | False rejects | Filter CANNOT_TELL | \"?\" | Kept in set B | Kept, all 1167 |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for name, desc, _, _ in EXPERIMENTS:
        s = stats[name]
        L.append(f"| {name} | {desc} | {s['judged']} | {s['agree']} | {pct(s['agree'], s['judged'])} | "
                 f"{s['false_keep']} | {s['false_reject']} | {s['cannot_tell']} | {s['question']} | "
                 f"{s['kept_B']} | {s['kept_all']} |")

    L += ["", "### Difference from baseline (in postings; n = 30)", "",
          "| Run | Δ agree | Δ false keeps | Δ false rejects | Δ kept in set B | Δ kept, all 1167 | Set B postings whose decision changed |",
          "|---|---|---|---|---|---|---|"]
    for name, _, _, _ in EXPERIMENTS[1:]:
        s = stats[name]
        changed = [k for k in runs[base_name][1]
                   if runs[base_name][1][k].decision != runs[name][1][k].decision]
        in_b = {(lab["provider"], lab["id"]) for lab in labels}
        changed_b = [k for k in changed if k in in_b]
        L.append(f"| {name} | {signed(s['agree'] - base['agree'])} | {signed(s['false_keep'] - base['false_keep'])} | "
                 f"{signed(s['false_reject'] - base['false_reject'])} | {signed(s['kept_B'] - base['kept_B'])} | "
                 f"{signed(s['kept_all'] - base['kept_all'])} | {len(changed_b)} |")

    L += ["", "### Postings whose decision changed (all 1167, for context; only set B rows are measured)", ""]
    for name, _, _, _ in EXPERIMENTS[1:]:
        changed = sorted(k for k in runs[base_name][1]
                         if runs[base_name][1][k].decision != runs[name][1][k].decision)
        in_b = {(lab["provider"], lab["id"]): lab["my_verdict"].strip() for lab in labels}
        L += [f"**{name}:** {len(changed)} posting(s)", ""]
        if changed:
            L += ["| Provider/id | Title | Baseline | This run | Score | rules_fired | In set B (my verdict) |",
                  "|---|---|---|---|---|---|---|"]
            for k in changed:
                a, b = runs[base_name][1][k], runs[name][1][k]
                L.append(f"| {k[0]}/{k[1]} | {titles[k].replace('|', chr(92) + '|')} | {a.decision} | {b.decision} | "
                         f"{b.score} | {';'.join(b.rules_fired)} | {in_b.get(k, 'no')} |")
            L.append("")

    L += ["## Interpretation", "", "_To be written by me._", ""]
    return "\n".join(L)


def main() -> int:
    report = build()
    out = cfg.PROJECT_ROOT / REPORT
    out.write_text(report, encoding="utf-8")
    print(report)
    print(f"\nwrote {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
