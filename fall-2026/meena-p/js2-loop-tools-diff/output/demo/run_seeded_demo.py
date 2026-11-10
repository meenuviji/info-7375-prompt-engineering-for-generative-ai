"""SEEDED, OFFLINE demo runner. Never touches the network.

Runs the JS2 loop on one board (greenhouse/cloudflare) whose only response is a fixture
file, using the same fake transport the tests use (tests/helpers.py: Sandbox,
ScriptedTransport). The loop runs in a temporary project root, so the real output/states/
and traces/ are not touched. The run's trace is copied to the given path (never
overwritten), and the process exits with the run's exit code.

    .venv/bin/python output/demo/run_seeded_demo.py FIXTURE OUT_TRACE
"""

import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT))

from tests.helpers import RUN_ID, Sandbox, gh, url  # noqa: E402


def main(fixture: str, out_trace: str) -> int:
    body = Path(fixture).read_bytes()
    sb = Sandbox([gh("cloudflare")])
    try:
        report = sb.run({url("greenhouse", "cloudflare"): [{"status": 200, "body": body, "latency": 0.05}]})
        trace = (sb.root / "traces" / f"trace_{RUN_ID}.jsonl").read_bytes()
    finally:
        sb.cleanup()
    out = Path(out_trace)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "xb") as f:  # never overwrite an earlier demo trace
        f.write(trace)
    (board,) = report["boards"]
    print(json.dumps({
        "status": report["status"],
        "exit_code": report["exit_code"],
        "requests_used": report["budget"]["requests_used"],
        "board": board["board"],
        "outcome": board["outcome"],
        "job_count": board["job_count"],
        "error_code": board["error_code"],
        "observations": board["observations"],
        "trace_saved_to": str(out),
    }, indent=2))
    return report["exit_code"]


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
