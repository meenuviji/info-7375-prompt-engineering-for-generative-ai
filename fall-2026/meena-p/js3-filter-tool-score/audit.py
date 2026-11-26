"""Audit set A: compare my blind verdicts with the filter's decisions.

Usage: .venv/bin/python audit.py
Reads (never writes) labels/set_A_labels.csv, labels/set_A_key.csv, output/filter_results.csv
and data/raw/. Writes audit/AUDIT_REPORT_DRAFT.md and prints the same report.

Definitions (computed, no interpretation):
- agree:        filter KEPT and verdict y, or filter REJECTED and verdict n
- filter error: filter REJECTED and verdict y, or filter KEPT and verdict n
- "?":          my "cannot tell" answers, counted on their own, never in agree or error
- filter CANNOT_TELL rows with a y/n verdict are counted on their own too
- error proportion for the random rejects: errors / (y + n answers); "?" are excluded from
  the denominator and reported next to it. 95% Wilson score interval, z = 1.96.
  If errors are 0, the rule-of-three upper bound 3/n is also given.
- candidate false friends: every rule that fired on a set A posting I marked n or ?,
  with the word it matched and the sentence (or title) it matched in. Whether a match is a
  real false friend is my judgment, not this script's.
"""

import csv
import math
import re
from collections import Counter

from src import config as cfg
from src.filter import EXCLUSION_RE, ROLE_RE, TOPIC_RE
from src.postings import load_postings

Z = 1.96
GROUPS = [("random_rejected", "Random rejects"), ("close_call", "Close calls"), ("random_kept", "Kept")]
REPORT = "audit/AUDIT_REPORT_DRAFT.md"


def read_csv(rel):
    with open(cfg.PROJECT_ROOT / rel, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def wilson(k: int, n: int, z: float = Z) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def classify(decision: str, verdict: str) -> str:
    if verdict == "?":
        return "?"
    if decision == cfg.CANNOT_TELL:
        return "filter_cannot_tell"
    if (decision, verdict) in {(cfg.KEPT, "y"), (cfg.REJECTED, "n")}:
        return "agree"
    if (decision, verdict) in {(cfg.REJECTED, "y"), (cfg.KEPT, "n")}:
        return "error"
    raise ValueError(f"unexpected decision/verdict: {decision!r}/{verdict!r}")


def sentence_at(text: str, pos: int) -> str:
    start = max(text.rfind("\n", 0, pos), *(text.rfind(p, 0, pos) for p in (". ", "! ", "? ")))
    start = 0 if start < 0 else start + 1
    ends = [i for i in (text.find("\n", pos), *(text.find(p, pos) for p in (". ", "! ", "? "))) if i >= 0]
    end = min(ends) + 1 if ends else len(text)
    return " ".join(text[start:end].split())


def matches(posting) -> list[tuple[str, str, str, str]]:
    """(rule, field, matched word, sentence) for the first match of each rule that fires."""
    out = []
    for compiled, field in ((ROLE_RE, "title"), (TOPIC_RE, "description"), (EXCLUSION_RE, "title")):
        text = posting.title if field == "title" else posting.description
        for rule, rx in compiled.items():
            m = rx.search(text or "")
            if m:
                sentence = text if field == "title" else sentence_at(text, m.start())
                out.append((rule, field, m.group(0), sentence))
    return out


def md_escape(s: str) -> str:
    return s.replace("|", "\\|")


def build_report() -> str:
    labels = read_csv("labels/set_A_labels.csv")
    keys = {(r["provider"], r["id"]): r for r in read_csv("labels/set_A_key.csv")}
    results = {(r["provider"], r["id"]): r for r in read_csv(cfg.RESULTS_CSV)}
    postings = {(p.provider, p.id): p for p in load_postings()[0]}

    joined = []
    for lab in labels:
        k = (lab["provider"], lab["id"])
        verdict = lab["my_verdict"].strip()
        if verdict not in {"y", "n", "?"}:
            raise ValueError(f"{k}: verdict {verdict!r} is not y, n or ?; label every row first")
        res = results[k]
        joined.append({**res, "why": keys[k]["why_sampled"], "verdict": verdict,
                       "reason": lab["my_reason"].strip(), "outcome": classify(res["decision"], verdict)})

    n_rejected_all = sum(r["decision"] == cfg.REJECTED for r in results.values())
    L = ["# Set A audit — DRAFT",
         "",
         "**Computed by audit.py; interpretation to be written by me.**",
         "",
         f"Inputs: `labels/set_A_labels.csv` ({len(joined)} rows), `labels/set_A_key.csv`, "
         f"`{cfg.RESULTS_CSV}` (filter FILTER.md v1, keep threshold {cfg.KEEP_THRESHOLD}).",
         "Agree = filter KEPT & y, or filter REJECTED & n. Filter error = filter REJECTED & y, "
         "or filter KEPT & n. \"?\" answers are counted separately and are in neither.",
         ""]

    # 1. tables
    L.append("## 1. Agreement by sampling group")
    for why, name in GROUPS:
        rows = [r for r in joined if r["why"] == why]
        c = Counter(r["outcome"] for r in rows)
        dec = Counter(r["decision"] for r in rows)
        L += ["", f"### {name} (n = {len(rows)}; filter decisions: "
              + ", ".join(f"{d} {dec[d]}" for d in cfg.DECISIONS if dec[d]) + ")", "",
              "| Outcome | Count |", "|---|---|",
              f"| Agree with filter | {c['agree']} |",
              f"| Filter error | {c['error']} |",
              f"| My \"?\" (cannot tell) | {c['?']} |"]
        if c["filter_cannot_tell"]:
            L.append(f"| Filter CANNOT_TELL, my y/n | {c['filter_cannot_tell']} |")
    L.append("")

    # 2. random rejects
    rej = [r for r in joined if r["why"] == "random_rejected"]
    k = sum(r["outcome"] == "error" for r in rej)
    q = sum(r["outcome"] == "?" for r in rej)
    n = len(rej) - q
    lo, hi = wilson(k, n)
    L += ["## 2. Random rejects: error proportion", "",
          f"- Sample: {len(rej)} postings drawn at random (seed {cfg.SEED}) from the {n_rejected_all} "
          f"postings the filter REJECTED. \"?\" answers: {q} (excluded from the denominator).",
          f"- **In this sample of {n}:** I labeled {k} of {n} as relevant (y), so the filter "
          f"rejected {k} relevant posting{'s' if k != 1 else ''} in this sample ({k}/{n} = {k / n:.3f}).",
          f"- **Estimate for all {n_rejected_all} rejects:** error proportion {k / n:.3f}, "
          f"95% Wilson interval [{lo:.3f}, {hi:.3f}] "
          f"(about {lo * n_rejected_all:.0f} to {hi * n_rejected_all:.0f} of {n_rejected_all} rejects, "
          "if the sample is representative).",
          ]
    if k == 0:
        L.append(f"- Errors are 0, so the rule-of-three 95% upper bound is 3/{n} = {3 / n:.3f}.")
    L += ["- This is an estimate for the filter's rejects in this data snapshot, from one labeler; "
          "it is not a measured rate for all postings.", ""]

    # 3a. disagreements
    L += ["## 3. Postings where the filter and I disagree (filter errors)", "",
          "| Group | Filter | Score | My verdict | Title | rules_fired | my_reason |", "|---|---|---|---|---|---|---|"]
    errs = [r for r in joined if r["outcome"] == "error"]
    for r in errs:
        L.append(f"| {r['why']} | {r['decision']} | {r['score']} | {r['verdict']} | {md_escape(r['title'])} | "
                 f"{r['rules_fired']} | {md_escape(r['reason']) or '(none)'} |")
    if not errs:
        L.append("| — | — | — | — | (none) | — | — |")
    unsure = [r for r in joined if r["outcome"] in {"?", "filter_cannot_tell"}]
    L += ["", f"\"?\" answers and filter CANNOT_TELL rows (listed separately): {len(unsure)}"]
    for r in unsure:
        L.append(f"- {r['why']} | {r['decision']} | {r['verdict']} | {r['title']} | {r['rules_fired']} | "
                 f"{r['reason'] or '(none)'}")
    L.append("")

    # 3b. candidate false friends
    L += ["## 4. Candidate false friends", "",
          "Every rule that fired on a set A posting I marked n or ?, with the matched word and the "
          "sentence it matched in (title rules show the title). Candidates only: which of these "
          "fired for a reason unrelated to the persona is for me to judge.", "",
          "| Posting (group, filter) | My verdict | Rule | Field | Matched word | Sentence |", "|---|---|---|---|---|---|"]
    n_cand = 0
    for r in joined:
        if r["verdict"] not in {"n", "?"}:
            continue
        for rule, field, word, sentence in matches(postings[(r["provider"], r["id"])]):
            n_cand += 1
            L.append(f"| {md_escape(r['title'])} ({r['why']}, {r['decision']}) | {r['verdict']} | {rule} | "
                     f"{field} | `{word}` | {md_escape(sentence)} |")
    L += ["", f"Candidate matches: {n_cand}.", "",
          "## Interpretation", "", "_To be written by me._", ""]
    return "\n".join(L)


def main() -> int:
    report = build_report()
    out = cfg.PROJECT_ROOT / REPORT
    out.parent.mkdir(exist_ok=True)
    out.write_text(report, encoding="utf-8")
    print(report)
    print(f"\nwrote {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
