"""CLI: python -m agent.run --label live | --from-file <path> --label <label>
          python -m agent.run --rejudge <evidence/runs/...json>   (judges only; state untouched)"""

import argparse
import json
import sys
from pathlib import Path

from agent import claude_judge, fetch, persona, rule_judge, state
from agent.validate import check_alignment

RUNS_DIR = Path("evidence/runs")


def judge_postings(jobs: list[dict], resume: dict, run_out: Path, source: str,
                   claude_call=None, calls_log: Path | None = None) -> Path:
    """Both judges on each posting; writes <run>_verdicts.json next to the run output."""
    model, model_source = claude_judge.judge_model()
    verdicts = []
    for job in jobs:
        r = rule_judge.judge(job, resume)
        c = claude_judge.judge(job, resume, call=claude_call, log_path=calls_log)
        verdicts.append({
            "posting_id": job["id"],
            "title": job["title"],
            "rule_verdict": r["verdict"],
            "rule_justification": r["justification"],
            "claude_verdict": c["verdict"],
            "claude_justification": c["justification"],
            "rule": r,
            "claude": c,
        })
    checked = [{k: v[k] for k in ("posting_id", "rule_justification")}
               | ({"claude_justification": v["claude_justification"]}
                  if v["claude_justification"] is not None else {})
               for v in verdicts]
    out = run_out.with_name(run_out.stem + "_verdicts.json")
    out.write_text(json.dumps({
        "run": run_out.name,
        "source": source,
        "judge_model": model,
        "judge_model_source": model_source,
        "prompt_file": claude_judge.PROMPT_PATH.name,
        "system_prompt_file": claude_judge.SYSTEM_PATH.name,
        "rule_kind": "RECORD",
        "claude_kind": claude_judge.JUDGMENT_LABEL,
        "alignment_errors": check_alignment(checked, jobs),
        "verdicts": verdicts,
    }, indent=2, ensure_ascii=False) + "\n")
    return out


def run(label: str, from_file: Path | None, state_path: Path, persona_path: Path,
        runs_dir: Path, judge: bool = False, claude_call=None) -> dict:
    fetch.safe_label(label)
    resume = persona.load_persona(persona_path)  # raises PersonaError: refuse before any fetch

    source = from_file if from_file else fetch.fetch_board(label)
    board = json.loads(Path(source).read_text())

    ids = state.posting_ids(board)
    seen = state.load_seen(state_path)
    new = state.new_ids(ids, seen)

    jobs = {j["id"]: j for j in board["jobs"]}
    result = {
        "label": label,
        "source": str(source),
        "fetched_live": from_file is None,
        "run_at_utc": fetch.utc_timestamp(),
        "baseline": seen is None,
        "previous_state_count": None if seen is None else len(seen),
        "postings_in_response": len(ids),
        "new_count": len(new),
        "new_postings": [
            {"id": i, "title": jobs[i]["title"],
             "location": (jobs[i].get("location") or {}).get("name")}
            for i in new
        ],
    }
    runs_dir.mkdir(parents=True, exist_ok=True)
    out = runs_dir / f"{result['run_at_utc']}_{label}.json"
    out.write_text(json.dumps(result, indent=2) + "\n")
    result["output"] = str(out)
    if judge and new:
        result["verdicts_output"] = str(judge_postings(
            [jobs[i] for i in new], resume, out, str(source), claude_call))
    # Only after both judges produced output for every new posting; a judging error
    # above leaves state untouched, so those postings are reported as new again next run.
    state.save_seen(ids, state_path)
    return result


def rejudge(run_file: Path, persona_path: Path) -> Path:
    """Re-run both judges on a saved run's new postings, from its saved raw source."""
    resume = persona.load_persona(persona_path)
    r = json.loads(run_file.read_text())
    board = json.loads(Path(r["source"]).read_text())
    jobs = {j["id"]: j for j in board["jobs"]}
    return judge_postings([jobs[p["id"]] for p in r["new_postings"]], resume, run_file,
                          r["source"])


def print_verdicts(path: Path) -> None:
    v = json.loads(path.read_text())
    print(f"judge_model={v['judge_model']} ({v['judge_model_source']}) "
          f"prompt={v['prompt_file']} alignment_errors={len(v['alignment_errors'])}")
    for x in v["verdicts"]:
        print(f"  {x['posting_id']}  RECORD rule={x['rule_verdict']}  "
              f"JUDGMENT claude={x['claude_verdict']}  {x['title']}")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="agent.run")
    p.add_argument("--label")
    p.add_argument("--from-file", type=Path, help="run against a saved response; no fetch")
    p.add_argument("--rejudge", type=Path, help="re-run judges on a saved run's new postings")
    p.add_argument("--no-judge", action="store_true", help="skip both judges")
    p.add_argument("--state", type=Path, default=state.STATE_PATH)
    p.add_argument("--persona", type=Path, default=persona.PERSONA_PATH)
    p.add_argument("--runs-dir", type=Path, default=RUNS_DIR)
    a = p.parse_args(argv)
    if not a.rejudge and not a.label:
        p.error("--label is required unless --rejudge is given")
    try:
        if a.rejudge:
            out = rejudge(a.rejudge, a.persona)
            print_verdicts(out)
            print(f"wrote {out}")
            return 0
        r = run(a.label, a.from_file, a.state, a.persona, a.runs_dir, judge=not a.no_judge)
    except (persona.PersonaError, fetch.HostNotAllowedError) as e:
        print(e, file=sys.stderr)
        return 2
    kind = "BASELINE" if r["baseline"] else "RUN"
    print(f"{kind} label={r['label']} source={r['source']} "
          f"postings={r['postings_in_response']} new={r['new_count']}")
    for j in r["new_postings"]:
        print(f"  NEW {j['id']}  {j['title']}  [{j['location']}]")
    print(f"wrote {r['output']}")
    if "verdicts_output" in r:
        print_verdicts(Path(r["verdicts_output"]))
        print(f"wrote {r['verdicts_output']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
