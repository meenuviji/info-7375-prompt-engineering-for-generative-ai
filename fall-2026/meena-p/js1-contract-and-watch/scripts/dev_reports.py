"""Sampling report and judge_v1 dev baseline. Dev rows only; heldout rows are never judged.

  python scripts/dev_reports.py run      # makes the Claude calls, saves evidence/runs/*.json
  python scripts/dev_reports.py render   # writes reports/ from the saved evidence

Heldout rows contribute only their split and my_label to the per-split label counts.
"""

import csv
import json
import random
import sys
from collections import Counter
from pathlib import Path

from agent import claude_judge, persona, rule_judge
from agent.fetch import utc_timestamp

SEED = 7375
SHEET = Path("labels/postings_20.csv")
RAW = Path("evidence/raw/20261031T182100Z_live.json")
RUNS = Path("evidence/runs")
REPORTS = Path("reports")
SAMPLING_FIXED = [8043974, 8221248]  # both clause1_pass dev rows
N_SAMPLING_EXTRA, N_REPEATS = 3, 4


def load_sheet():
    with SHEET.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    counts = Counter((r["split"], r["my_label"]) for r in rows)
    label_counts = {s: {l: counts[(s, l)] for l in ("relevant", "not_relevant")}
                    for s in ("dev", "heldout")}
    dev = [{k: r[k] for k in ("posting_id", "selection_group", "title", "my_label")}
           for r in rows if r["split"] == "dev"]
    for r in dev:
        r["posting_id"] = int(r["posting_id"])
    return label_counts, sorted(dev, key=lambda r: r["posting_id"])


def sampling_ids(dev):
    by_id = {r["posting_id"]: r for r in dev}
    assert all(by_id[i]["selection_group"] == "clause1_pass" for i in SAMPLING_FIXED)
    pool = sorted(i for i in by_id if i not in SAMPLING_FIXED)
    return SAMPLING_FIXED + sorted(random.Random(SEED).sample(pool, N_SAMPLING_EXTRA))


def run():
    resume = persona.load_persona()
    label_counts, dev = load_sheet()
    jobs = {j["id"]: j for j in json.loads(RAW.read_text())["jobs"]}
    ts = utc_timestamp()
    model, model_source = claude_judge.judge_model()
    common = {"run_at_utc": ts, "source": str(RAW), "sheet": str(SHEET),
              "judge_model": model, "judge_model_source": model_source,
              "prompt_file": claude_judge.PROMPT_PATH.name,
              "system_prompt_file": claude_judge.SYSTEM_PATH.name}
    by_id = {r["posting_id"]: r for r in dev}

    sids = sampling_ids(dev)
    sampling = []
    for pid in sids:
        calls = [claude_judge.judge(jobs[pid], resume, max_attempts=1,
                                    tag=f"sampling_dev_{ts}_call{k}")
                 for k in range(1, N_REPEATS + 1)]
        sampling.append({**by_id[pid], "rule": rule_judge.judge(jobs[pid], resume),
                         "calls": calls})
    s_out = RUNS / f"{ts}_sampling_dev.json"
    s_out.write_text(json.dumps({**common, "seed": SEED, "repeats": N_REPEATS,
                                 "postings": sampling}, indent=2, ensure_ascii=False) + "\n")

    experiment = []
    for r in dev:
        pid = r["posting_id"]
        experiment.append({**r, "rule": rule_judge.judge(jobs[pid], resume),
                           "v1": claude_judge.judge(jobs[pid], resume,
                                                    tag=f"experiment_v1_dev_{ts}")})
    e_out = RUNS / f"{ts}_experiment_v1_dev.json"
    e_out.write_text(json.dumps({**common, "label_counts": label_counts,
                                 "postings": experiment}, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {s_out}\nwrote {e_out}")


def latest(suffix):
    return sorted(RUNS.glob(f"*_{suffix}.json"))[-1]


def md_cell(s):
    return str(s).replace("|", "\\|").replace("\n", " ")


def render():
    sp, ep = latest("sampling_dev"), latest("experiment_v1_dev")
    S, E = json.loads(sp.read_text()), json.loads(ep.read_text())
    date = f"{S['run_at_utc'][:4]}-{S['run_at_utc'][4:6]}-{S['run_at_utc'][6:8]}"
    reported = sorted({m for p in S["postings"] for c in p["calls"]
                       for m in (c.get("model_reported") or [])})

    # ---- SAMPLING.md
    n_calls = sum(len(p["calls"]) for p in S["postings"])
    invalid = sum(c["verdict"] == "INVALID" for p in S["postings"] for c in p["calls"])
    L = [
        "# Sampling report (Chapter 1)", "",
        f"- Date (UTC): {date}, run `{S['run_at_utc']}`",
        f"- Model: `{S['judge_model']}` ({S['judge_model_source']}); "
        f"model reported by backend: {', '.join(f'`{m}`' for m in reported) or 'n/a'}",
        f"- Prompts: `prompts/{S['system_prompt_file']}` (system), "
        f"`prompts/{S['prompt_file']}` (user)",
        f"- Calls: {n_calls} ({len(S['postings'])} postings x {S['repeats']}), each a fresh, "
        "stateless call with no retry. All logged to `evidence/claude_calls.jsonl` "
        f"(tag `sampling_dev_{S['run_at_utc']}_call<k>`).",
        f"- Invalid outputs: {invalid} of {n_calls}",
        f"- Raw results: `{sp}`",
        "- Postings: the 2 `clause1_pass` dev rows (8043974, 8221248) plus 3 more dev rows "
        f"sampled with seed {S['seed']} from the other 8 dev rows (id-sorted). Dev split only.",
        "- Claude verdicts are JUDGMENT (model output, not fact). Rule verdicts are RECORD.",
        "", "## Verdicts per posting per call", "",
        "| posting_id | title | group | my_label | rule (RECORD) | call 1 | call 2 | call 3 "
        "| call 4 | distinct verdicts | agree with my_label |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for p in S["postings"]:
        vs = [c["verdict"] for c in p["calls"]]
        agree = sum(v == p["my_label"] for v in vs)
        L.append(f"| {p['posting_id']} | {md_cell(p['title'])} | {p['selection_group']} | "
                 f"{p['my_label']} | {p['rule']['verdict']} | " + " | ".join(vs) +
                 f" | {len(set(vs))} ({', '.join(sorted(set(vs)))}) | {agree}/{len(vs)} |")
    L += [
        "", "## What this can and cannot show", "",
        "- Identical verdicts across repeats show repeatability, not correctness. A judge can be "
        "consistently wrong.",
        f"- {S['repeats']} samples per posting cannot estimate a rate. They can show that "
        "verdicts vary on a posting, but a posting that gave the same verdict 4 times may "
        "still flip on a later call.",
        "- Agreement is measured against one person's labels (Meena's, under LABELING.md), "
        "not against ground truth.",
        "- All 10 dev labels are `not_relevant`, so this sample only measures agreement on "
        "postings labeled negative.",
        "", "## My conclusion", "",
    ]
    (REPORTS / "SAMPLING.md").write_text("\n".join(L))

    # ---- EXPERIMENT.md
    lc = E["label_counts"]
    rows = E["postings"]
    k = sum(r["v1"]["verdict"] == r["my_label"] for r in rows)
    k_rule = sum(r["rule"]["verdict"] == r["my_label"] for r in rows)
    const = sum(r["my_label"] == "not_relevant" for r in rows)
    v1_invalid = sum(r["v1"]["verdict"] == "INVALID" for r in rows)
    retries = sum(r["v1"]["attempts"] > 1 for r in rows)
    L = [
        "# Prompt experiment: judge_v1 baseline on dev", "",
        f"- Date (UTC): {date}, run `{E['run_at_utc']}`",
        f"- Model: `{E['judge_model']}` ({E['judge_model_source']})",
        f"- Prompts: `prompts/{E['system_prompt_file']}` (system), "
        f"`prompts/{E['prompt_file']}` (user)",
        "- One judgment per dev posting (validator allows one retry on invalid output; "
        f"{retries} retries used, {v1_invalid} INVALID). Calls logged to "
        f"`evidence/claude_calls.jsonl` (tag `experiment_v1_dev_{E['run_at_utc']}`).",
        f"- Raw results: `{ep}`",
        "- v1 verdicts are JUDGMENT (model output, not fact). Rule verdicts are RECORD.",
        "", "## My label counts per split", "",
        "| split | relevant | not_relevant |", "|---|---|---|",
        *[f"| {s} | {lc[s]['relevant']} | {lc[s]['not_relevant']} |" for s in ("dev", "heldout")],
        "", "## Dev results", "",
        "| posting_id | my_label | rule verdict (RECORD) | v1 verdict (JUDGMENT) | match |",
        "|---|---|---|---|---|",
        *[f"| {r['posting_id']} | {r['my_label']} | {r['rule']['verdict']} | "
          f"{r['v1']['verdict']} | {'yes' if r['v1']['verdict'] == r['my_label'] else 'no'} |"
          for r in rows],
        "", "## Pass rate", "",
        f"- judge_v1 vs my labels: **{k}/10**",
        f"- Baseline to beat: a constant `not_relevant` judge scores **{const}/10** on dev.",
        f"- For reference, the rule judge (RECORD) vs my labels: {k_rule}/10.",
    ]
    if const == 10:
        L.append("- Because every dev label is `not_relevant`, the constant baseline is already "
                 "at the maximum (10/10). On this dev set no judge can beat it, only tie it.")
    L += ["", "## Misses", ""]
    misses = [r for r in rows if r["v1"]["verdict"] != r["my_label"]]
    if not misses:
        L.append("None: v1 matched my label on all 10 dev postings.")
    for r in misses:
        v = r["v1"]
        L += [f"### {r['posting_id']}: {r['title']}", "",
              f"- my_label: `{r['my_label']}`; v1: `{v['verdict']}`; rule: `{r['rule']['verdict']}`",
              f"- v1 cited: resume {v['resume_fields']}, posting {v['posting_fields']}"]
        if v["verdict"] == "INVALID":
            L += ["- Raw model output (rejected by validator):", ""]
            L += [f"  ```\n  {t}\n  ```" for t in v["raw_text"]]
        else:
            L.append(f"- v1 justification (JUDGMENT): {v['justification']}")
        L.append("")
    L += ["", "## The one change I chose and why", ""]
    (REPORTS / "EXPERIMENT.md").write_text("\n".join(L))
    print(f"wrote {REPORTS / 'SAMPLING.md'}\nwrote {REPORTS / 'EXPERIMENT.md'}")


if __name__ == "__main__":
    REPORTS.mkdir(exist_ok=True)
    {"run": run, "render": render}[sys.argv[1]]()
