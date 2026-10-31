"""judge_v2 on dev, then v1 and v2 on held-out (first time held-out is judged).

  python scripts/heldout_eval.py run      # Claude calls; saves evidence/runs/*_v2_eval.json
  python scripts/heldout_eval.py render   # appends results sections to reports/EXPERIMENT.md

Refuses to run unless judge_v1.txt, judge_v2.txt and system_v1.txt match the commit that
fixed v2 (V2_FIXED_COMMIT).
"""

import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from agent import claude_judge, persona, rule_judge
from agent.fetch import utc_timestamp

V2_FIXED_COMMIT = "8cbaad6"
V1_DEV_COMMIT = "f4fec9d"
LABELS_COMMIT = "c3732b9"
SHEET = Path("labels/postings_20.csv")
RAW = Path("evidence/raw/20261031T182100Z_live.json")
RUNS = Path("evidence/runs")
REPORT = Path("reports/EXPERIMENT.md")
V1, V2 = Path("prompts/judge_v1.txt"), Path("prompts/judge_v2.txt")
UNDEFINED = "precision undefined (no positive predictions)"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def committed_bytes(commit: str, p: Path) -> bytes:
    return subprocess.run(["git", "show", f"{commit}:{p}"], capture_output=True,
                          check=True).stdout


def load_split(split: str) -> list[dict]:
    with SHEET.open(newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["split"] == split]
    return sorted(({"posting_id": int(r["posting_id"]), "title": r["title"],
                    "selection_group": r["selection_group"], "my_label": r["my_label"]}
                   for r in rows), key=lambda r: r["posting_id"])


def run():
    for p in (V1, V2, claude_judge.SYSTEM_PATH):
        assert p.read_bytes() == committed_bytes(V2_FIXED_COMMIT, p), f"{p} differs from {V2_FIXED_COMMIT}"
    resume = persona.load_persona()
    jobs = {j["id"]: j for j in json.loads(RAW.read_text())["jobs"]}
    ts = utc_timestamp()
    model, model_source = claude_judge.judge_model()

    def judge_all(rows, prompt, tag):
        return [claude_judge.judge(jobs[r["posting_id"]], resume, prompt_path=prompt,
                                   tag=f"{tag}_{ts}") for r in rows]

    dev, held = load_split("dev"), load_split("heldout")
    out = {
        "run_at_utc": ts, "source": str(RAW), "sheet": str(SHEET),
        "judge_model": model, "judge_model_source": model_source,
        "system_prompt_file": claude_judge.SYSTEM_PATH.name,
        "prompt_sha256": {p.name: sha(p) for p in (V1, V2, claude_judge.SYSTEM_PATH)},
        "v2_fixed_commit": V2_FIXED_COMMIT,
        "dev": [{**r, "rule": rule_judge.judge(jobs[r["posting_id"]], resume), "v2": v}
                for r, v in zip(dev, judge_all(dev, V2, "experiment_v2_dev"))],
    }
    # Held-out is judged only after the dev run above and after v2 was committed.
    v1h = judge_all(held, V1, "experiment_v1_heldout")
    v2h = judge_all(held, V2, "experiment_v2_heldout")
    out["heldout"] = [{**r, "rule": rule_judge.judge(jobs[r["posting_id"]], resume),
                       "v1": a, "v2": b} for r, a, b in zip(held, v1h, v2h)]
    path = RUNS / f"{ts}_v2_eval.json"
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {path}")


def stats(rows, key):
    pred = [r[key]["verdict"] for r in rows]
    labels = [r["my_label"] for r in rows]
    k = sum(p == l for p, l in zip(pred, labels))
    pos_pred = sum(p == "relevant" for p in pred)
    pos_lab = sum(l == "relevant" for l in labels)
    if pos_lab == 0 or pos_pred == 0:
        prec = UNDEFINED
    else:
        tp = sum(p == l == "relevant" for p, l in zip(pred, labels))
        prec = f"{tp}/{pos_pred}"
    return {"k": k, "n": len(rows), "invalid": pred.count("INVALID"),
            "pos_pred": pos_pred, "precision": prec}


def render():
    E = json.loads(sorted(RUNS.glob("*_v2_eval.json"))[-1].read_text())
    v1dev = json.loads(sorted(RUNS.glob("*_experiment_v1_dev.json"))[-1].read_text())
    v1d = {r["posting_id"]: r["v1"] for r in v1dev["postings"]}
    dev, held = E["dev"], E["heldout"]
    for r in dev:
        r["v1"] = v1d[r["posting_id"]]
    calls = [json.loads(l) for l in Path("evidence/claude_calls.jsonl").read_text().splitlines()]
    first_held = min(c["ts_utc"] for c in calls if "heldout" in (c.get("tag") or ""))
    n_held_before = sum("heldout" in (c.get("tag") or "") for c in calls
                        if c["ts_utc"] < "2026-10-31T19:25:11Z")
    ts = E["run_at_utc"]
    date = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}"
    cells = {("dev", "v1"): stats(dev, "v1"), ("dev", "v2"): stats(dev, "v2"),
             ("heldout", "v1"): stats(held, "v1"), ("heldout", "v2"): stats(held, "v2")}
    rel = {s: sum(r["my_label"] == "relevant" for r in rows) for s, rows in
           (("dev", dev), ("heldout", held))}
    const = {s: sum(r["my_label"] == "not_relevant" for r in rows) for s, rows in
             (("dev", dev), ("heldout", held))}

    def yn(r, k):
        return "yes" if r[k]["verdict"] == r["my_label"] else "no"

    L = [
        "", "## Results: v2 on dev, v1 and v2 on held-out", "",
        f"- Date (UTC): {date}; v2-dev and held-out run `{ts}`. "
        f"v1-dev run `{v1dev['run_at_utc']}` (above).",
        f"- Model: `{E['judge_model']}` ({E['judge_model_source']})",
        f"- Prompts: `prompts/{E['system_prompt_file']}` (system, unchanged) with "
        "`prompts/judge_v1.txt` or `prompts/judge_v2.txt` (user). sha256: "
        + ", ".join(f"`{n}` {h[:12]}" for n, h in E["prompt_sha256"].items()),
        f"- Raw results: `{sorted(RUNS.glob('*_v2_eval.json'))[-1]}`; calls logged to "
        "`evidence/claude_calls.jsonl`.",
        "- v1/v2 verdicts are JUDGMENT (model output, not fact). Rule verdicts are RECORD.",
        "", "### v2 on dev", "",
        "| posting_id | my_label | rule verdict (RECORD) | v1 (JUDGMENT) | v2 (JUDGMENT) | v2 match |",
        "|---|---|---|---|---|---|",
        *[f"| {r['posting_id']} | {r['my_label']} | {r['rule']['verdict']} | "
          f"{r['v1']['verdict']} | {r['v2']['verdict']} | {yn(r, 'v2')} |" for r in dev],
        "", "### Held-out", "",
        "| posting_id | my_label | rule verdict (RECORD) | v1 (JUDGMENT) | v2 (JUDGMENT) |",
        "|---|---|---|---|---|",
        *[f"| {r['posting_id']} | {r['my_label']} | {r['rule']['verdict']} | "
          f"{r['v1']['verdict']} | {r['v2']['verdict']} |" for r in held],
        "", "### Pass rates (match with my_label)", "",
        "| | dev | held-out |", "|---|---|---|",
        f"| judge_v1 | {cells['dev','v1']['k']}/10 | {cells['heldout','v1']['k']}/10 |",
        f"| judge_v2 | {cells['dev','v2']['k']}/10 | {cells['heldout','v2']['k']}/10 |",
        f"| constant `not_relevant` baseline | {const['dev']}/10 | {const['heldout']}/10 |",
        f"| rule judge (RECORD), for reference | "
        f"{sum(r['rule']['verdict'] == r['my_label'] for r in dev)}/10 | "
        f"{sum(r['rule']['verdict'] == r['my_label'] for r in held)}/10 |",
        "", "### Counts", "",
        "| | dev | held-out |", "|---|---|---|",
        f"| postings I labeled relevant | {rel['dev']} | {rel['heldout']} |",
        f"| v1 relevant predictions | {cells['dev','v1']['pos_pred']} | {cells['heldout','v1']['pos_pred']} |",
        f"| v2 relevant predictions | {cells['dev','v2']['pos_pred']} | {cells['heldout','v2']['pos_pred']} |",
        f"| v1 INVALID | {cells['dev','v1']['invalid']} | {cells['heldout','v1']['invalid']} |",
        f"| v2 INVALID | {cells['dev','v2']['invalid']} | {cells['heldout','v2']['invalid']} |",
        f"| v1 precision | {cells['dev','v1']['precision']} | {cells['heldout','v1']['precision']} |",
        f"| v2 precision | {cells['dev','v2']['precision']} | {cells['heldout','v2']['precision']} |",
        "", "## Limits", "",
        "- 10 cases per split.",
        "- One labeler (Meena), one model "
        f"(`{E['judge_model']}`), one board (Greenhouse `cloudflare`, one snapshot).",
        "- The board does not match the Boston-based persona: 0 of 464 postings have \"Boston\" "
        "in `posting.location.name`, 2 of 464 contain \"Remote\", and 1 of 464 lists an "
        "office named with Boston.",
        "- A 1-2 case difference between cells is not evidence of a difference.",
        f"- Held-out was opened only after v2 was fixed: labels committed in `{LABELS_COMMIT}` "
        f"(2026-10-31T19:11:03Z); v1 dev baseline in `{V1_DEV_COMMIT}` (19:15:52Z); "
        f"`prompts/judge_v2.txt` committed in `{V2_FIXED_COMMIT}` (19:25:11Z). "
        f"Held-out calls in the log before {V2_FIXED_COMMIT}: {n_held_before}; first "
        f"held-out call: {first_held}. The run checked that judge_v1.txt, judge_v2.txt and "
        f"system_v1.txt were "
        f"byte-identical to `{V2_FIXED_COMMIT}` before any call.",
        "",
    ]
    # Replace a previously rendered results block instead of appending a second copy.
    text = REPORT.read_text()
    marker = "\n## Results: v2 on dev"
    if marker in text:
        text = text[:text.index(marker)]
    REPORT.write_text(text + "\n".join(L))
    print(f"rendered results into {REPORT}")


if __name__ == "__main__":
    {"run": run, "render": render}[sys.argv[1]]()
