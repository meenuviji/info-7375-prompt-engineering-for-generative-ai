"""Structural validation of a 200 response body. Never decided by byte size.

Greenhouse: the root is an object with a "jobs" list and meta.total as an integer.
Lever: the root is a list. Every job is an object with an "id" (int or non-empty string).

Outcomes, following GATE.md section 4:
- verified: job_ids and job_count are set.
- an empty list counts as a verified 0 only when the metadata says 0 (Greenhouse
  meta.total == 0). Lever returns no metadata, so an empty Lever list is SUSPICIOUS_PAYLOAD.
- an empty list whose metadata reports jobs gives SUSPICIOUS_PAYLOAD.
- a body cut off mid-structure, or meta.total > len(jobs), gives TRUNCATED_RESPONSE.
- anything else that does not fit the schema gives PARSE_SCHEMA_MISMATCH.
A failure never carries a job count.
"""

import json
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Verdict:
    ok: bool
    job_ids: tuple | None = None
    job_count: int | None = None
    error_code: str | None = None
    observations: dict = field(default_factory=dict)
    detail: str | None = None


def _fail(code: str, detail: str, **observations) -> Verdict:
    return Verdict(ok=False, error_code=code, observations=observations, detail=detail)


def looks_truncated(text: str) -> bool:
    """True if text starts as JSON and ends inside an open string, array or object."""
    stripped = text.strip()
    if not stripped or stripped[0] not in "[{":
        return False
    closers = {"]": "[", "}": "{"}
    stack: list[str] = []
    in_string = escaped = False
    for ch in stripped:
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
        elif ch == '"':
            in_string = True
        elif ch in "[{":
            stack.append(ch)
        elif ch in closers:
            if not stack or stack[-1] != closers[ch]:
                return False  # mismatched closer: broken, not cut off
            stack.pop()
    return in_string or bool(stack)


def _job_ids(jobs: list) -> list | str:
    """The ids, or a message naming the first job without a valid id."""
    ids = []
    for i, job in enumerate(jobs):
        if not isinstance(job, dict) or "id" not in job:
            return f"job {i} has no 'id'"
        value = job["id"]
        if isinstance(value, bool) or not isinstance(value, (int, str)) or value == "":
            return f"job {i} has an invalid 'id': {value!r}"
        ids.append(value)
    return ids


def _greenhouse(data) -> Verdict:
    if not isinstance(data, dict) or not isinstance(data.get("jobs"), list):
        keys = sorted(data)[:10] if isinstance(data, dict) else type(data).__name__
        return _fail("PARSE_SCHEMA_MISMATCH", f"root must be an object with a 'jobs' list; got {keys}")
    jobs = data["jobs"]
    ids = _job_ids(jobs)
    if isinstance(ids, str):
        return _fail("PARSE_SCHEMA_MISMATCH", ids, jobs_in_body=len(jobs))
    meta = data.get("meta")
    total = meta.get("total") if isinstance(meta, dict) else None
    if isinstance(total, bool) or not isinstance(total, int) or total < 0:
        return _fail("PARSE_SCHEMA_MISMATCH", "meta.total missing or not a non-negative integer",
                     jobs_in_body=len(jobs))
    obs = {"meta_total": total, "jobs_in_body": len(jobs)}
    if not jobs:
        if total == 0:
            return Verdict(ok=True, job_ids=(), job_count=0, observations=obs)
        return _fail("SUSPICIOUS_PAYLOAD", f"empty jobs list but meta.total = {total}", **obs)
    # SEEDED REPRODUCTION (branch finished-wrong-demo only; never merge): the GATE.md 4.2
    # count check (meta.total > len(jobs) -> TRUNCATED_RESPONSE) is disabled on purpose to
    # show a finished-but-wrong run. See output/demo/FINISHED_WRONG.md.
    # if total > len(jobs):
    #     return _fail("TRUNCATED_RESPONSE", f"meta.total {total} > {len(jobs)} jobs in body",
    #                  truncation="count", **obs)
    if total < len(jobs):
        return _fail("PARSE_SCHEMA_MISMATCH", f"meta.total {total} < {len(jobs)} jobs in body", **obs)
    return Verdict(ok=True, job_ids=tuple(ids), job_count=len(ids), observations=obs)


def _lever(data) -> Verdict:
    if not isinstance(data, list):
        return _fail("PARSE_SCHEMA_MISMATCH", f"root must be a list; got {type(data).__name__}")
    if not data:
        return _fail("SUSPICIOUS_PAYLOAD", "empty list and Lever gives no count metadata to confirm 0",
                     jobs_in_body=0)
    ids = _job_ids(data)
    if isinstance(ids, str):
        return _fail("PARSE_SCHEMA_MISMATCH", ids, jobs_in_body=len(data))
    return Verdict(ok=True, job_ids=tuple(ids), job_count=len(ids), observations={"jobs_in_body": len(data)})


def parse_board(provider: str, body: bytes) -> Verdict:
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError as e:
        return _fail("PARSE_SCHEMA_MISMATCH", f"body is not UTF-8: {e}")
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, RecursionError) as e:
        if looks_truncated(text):
            return _fail("TRUNCATED_RESPONSE", f"JSON cut off mid-structure: {e}", truncation="syntax")
        return _fail("PARSE_SCHEMA_MISMATCH", f"body is not JSON: {e}")
    if provider == "greenhouse":
        return _greenhouse(data)
    if provider == "lever":
        return _lever(data)
    raise ValueError(f"unknown provider {provider!r}")  # unreachable: the config loader rejects it
