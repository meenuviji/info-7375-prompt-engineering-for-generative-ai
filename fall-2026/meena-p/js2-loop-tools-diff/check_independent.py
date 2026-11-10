"""Independent check of a JS2 run against the raw Greenhouse body it was given.

Imports nothing from this project: only the standard library (json, sys). It reads only
the two files named on the command line and recounts everything itself.

    .venv/bin/python -I check_independent.py FIXTURE TRACE

Prints the jobs in the body, meta.total, the count the trace reported, and a verdict.
Exit status: 0 if the run's report agrees with the body, 1 if it does not.
"""

import json
import sys


def main(fixture_path: str, trace_path: str) -> int:
    with open(fixture_path, encoding="utf-8") as f:
        body = json.load(f)
    jobs_in_body = len(body["jobs"])
    meta_total = body["meta"]["total"]

    with open(trace_path, encoding="utf-8") as f:
        events = [json.loads(line) for line in f if line.strip()]
    attempts = [e for e in events if e.get("event") == "ATTEMPT"]
    final = attempts[-1]  # the board's last attempt holds its outcome
    reported = final.get("job_count")
    error_code = final.get("error_code")
    status = next((e.get("status") for e in events if e.get("event") == "RUN_END"), None)

    print(f"fixture:              {fixture_path}")
    print(f"trace:                {trace_path}")
    print(f"jobs in body:         {jobs_in_body}")
    print(f"meta.total:           {meta_total}")
    print(f"count trace reported: {reported}")
    print(f"trace error_code:     {error_code}")
    print(f"run status (RUN_END): {status}")

    if meta_total > jobs_in_body and reported is not None:
        missing = meta_total - jobs_in_body
        print(f"verdict: WRONG - the run reported {reported} jobs as a verified count and ended "
              f"{status}, but the body advertises {meta_total}: {missing} postings are missing "
              f"from the response. A truncated response was accepted as complete.")
        return 1
    if meta_total > jobs_in_body and reported is None:
        print(f"verdict: CAUGHT - the body is short by {meta_total - jobs_in_body} postings and the run "
              f"reported no count ({error_code}), ending {status}.")
        return 0
    if reported == jobs_in_body == meta_total:
        print("verdict: CONSISTENT - the reported count matches both the body and meta.total.")
        return 0
    print("verdict: MISMATCH - the reported count does not match the body.")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
