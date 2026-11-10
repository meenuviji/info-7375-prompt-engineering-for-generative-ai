"""JS2 bounded loop. Contract: GATE.md.

    .venv/bin/python -m src.loop --config config/boards.json

For each board in the config, in order: check budgets, apply the repeat rule, fetch
(with retries only where the error policy allows), save the raw body, validate it
structurally, write one trace line per attempt, and update that board's state file.

A failed board is recorded and the loop moves on. Only loop-level failures stop the
run as FATAL_SYSTEM_ERROR: an unreadable or invalid config, an unreadable or corrupt
state file, a missing error-policy row, a policy refusal, or a filesystem failure.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import config as cfg
from .fetch import RequestsTransport, TransportError, safe_label, utc_timestamp
from .policy import GuardedIO, PolicyViolation, SecurityPolicy
from .state import StateError, diff_ids, load_state, next_state, save_state, state_path
from .validate import parse_board


class ConfigError(Exception):
    """Loop-level: the board config or the error policy is unusable."""


class BudgetExceeded(Exception):
    def __init__(self, limit: str):
        super().__init__(limit)
        self.limit = limit


@dataclass(frozen=True)
class Board:
    index: int
    provider: str
    token: str
    url: str
    deliberate: bool
    timeout: float | None

    @property
    def key(self) -> tuple[str, str, str, str]:
        # Repeat-rule key: (provider, token, method, url). The attempt number is NOT part of it.
        return (self.provider, self.token, "GET", self.url)

    def label(self) -> dict:
        return {"board": self.token, "provider": self.provider, "url": self.url, "deliberate": self.deliberate}


_BOARD_FIELDS = {"provider", "token", "deliberate", "timeout"}


def load_boards(io: GuardedIO, path: Path) -> list[Board]:
    try:
        raw = io.read_bytes(path)
    except OSError as e:
        raise ConfigError(f"cannot read config {path}: {e}") from e
    try:
        data = json.loads(raw)
    except (ValueError, RecursionError) as e:
        raise ConfigError(f"config {path} is not valid JSON: {e}") from e
    if not isinstance(data, dict) or not isinstance(data.get("boards"), list):
        raise ConfigError("config root must be an object with a 'boards' list")
    if set(data) - {"boards", "description"}:
        raise ConfigError(f"unknown config keys: {sorted(set(data) - {'boards', 'description'})}")

    boards: list[Board] = []
    provider_of: dict[str, str] = {}
    for i, entry in enumerate(data["boards"]):
        if not isinstance(entry, dict):
            raise ConfigError(f"board {i} must be an object")
        if set(entry) - _BOARD_FIELDS:
            raise ConfigError(f"board {i} has unknown keys: {sorted(set(entry) - _BOARD_FIELDS)}")
        provider = entry.get("provider")
        if provider not in cfg.PROVIDER_URLS:
            raise ConfigError(f"board {i}: unknown provider {provider!r}")
        token = entry.get("token")
        try:
            safe_label(token if isinstance(token, str) else "")
        except ValueError as e:
            raise ConfigError(f"board {i}: {e}") from e
        deliberate = entry.get("deliberate", False)
        if not isinstance(deliberate, bool):
            raise ConfigError(f"board {i}: deliberate must be true or false")
        timeout = entry.get("timeout")
        if timeout is not None and (isinstance(timeout, bool) or not isinstance(timeout, (int, float))
                                    or timeout <= 0):
            raise ConfigError(f"board {i}: timeout must be a positive number of seconds")
        # State files are keyed by token alone (GATE.md 5.1), so one token cannot name two providers.
        if provider_of.setdefault(token, provider) != provider:
            raise ConfigError(f"token {token!r} is listed under two providers; their state files would collide")
        boards.append(Board(i, provider, token, cfg.PROVIDER_URLS[provider].format(token=token),
                            deliberate, float(timeout) if timeout is not None else None))
    if not boards:
        raise ConfigError("config lists no boards")
    return boards


def check_error_policy(policy) -> None:
    if not policy:
        raise ConfigError("error policy is missing")
    missing = cfg.REQUIRED_POLICY_KINDS - set(policy)
    if missing:
        raise ConfigError(f"error policy has no row for: {sorted(missing)}")
    for kind, row in policy.items():
        if "code" not in row or "retry" not in row:
            raise ConfigError(f"error policy row {kind} needs 'retry' and 'code'")
        if row["retry"] and not (isinstance(row.get("max_retries"), int) and row["max_retries"] >= 0
                                 and isinstance(row.get("base_wait"), (int, float)) and row["base_wait"] >= 0):
            raise ConfigError(f"error policy row {kind} needs max_retries >= 0 and base_wait >= 0")


def classify_status(status: int) -> str | None:
    """Error-policy kind for an HTTP status; None for 200 (the body is validated next)."""
    if status == 200:
        return None
    if status == 404:
        return "HTTP_404"
    if status == 429:
        return "HTTP_429"
    if 500 <= status <= 599:
        return "HTTP_5XX"
    if 300 <= status <= 399:
        return "HTTP_3XX"
    return "HTTP_OTHER"


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Run:
    def __init__(self, *, root, config_path, transport, policy, clock, sleep, now_iso, run_id,
                 error_policy, budgets):
        self.root = root
        self.config_path = config_path
        self.transport = transport
        self.io = GuardedIO(policy)
        self.clock = clock
        self.sleep = sleep
        self.now_iso = now_iso
        self.run_id = run_id
        self.error_policy = error_policy
        self.budgets = dict(budgets)
        self.start = clock()
        self.requests_used = 0
        self.boards_started = 0
        self.seq = 0
        self.trace_path: Path | None = None
        self.trace_created = False
        self.raw_dir: Path | None = None
        self.raw_files: list[dict] = []
        self.malformed_files: list[dict] = []
        self.cache: dict[tuple, dict] = {}  # repeat cache: in memory, this run only
        self.results: list[dict] = []
        self.boards: list[Board] = []

    # --- helpers -----------------------------------------------------------
    def rel(self, path: Path | None) -> str | None:
        if path is None:
            return None
        try:
            return str(Path(path).relative_to(self.root))
        except ValueError:
            return str(path)

    def elapsed(self) -> float:
        return self.clock() - self.start

    def remaining_seconds(self) -> float:
        return self.budgets["max_seconds"] - self.elapsed()

    def budget_remaining(self) -> dict:
        return {
            "requests": self.budgets["max_requests"] - self.requests_used,
            "seconds": round(self.remaining_seconds(), 3),
            "boards": self.budgets["max_boards"] - self.boards_started,
        }

    def trace(self, **fields) -> None:
        self.seq += 1
        line = {"seq": self.seq, "run_id": self.run_id, "elapsed_seconds": round(self.elapsed(), 3), **fields}
        self.io.append_text(self.trace_path, json.dumps(line) + "\n")

    def save_raw(self, board: Board, attempt: int, body: bytes) -> tuple[str, str]:
        path = self.raw_dir / f"{board.provider}_{board.token}_attempt{attempt}.body"
        self.io.create_new(path, body)
        digest = hashlib.sha256(body).hexdigest()
        self.raw_files.append({"path": self.rel(path), "sha256": digest, "bytes": len(body)})
        return self.rel(path), digest

    def save_malformed(self, board: Board, attempt: int, body: bytes, code: str) -> str:
        directory = self.root / cfg.MALFORMED_DIR
        self.io.make_dirs(directory)
        path = directory / f"{self.run_id}_{board.provider}_{board.token}_attempt{attempt}.body"
        self.io.create_new(path, body)
        self.malformed_files.append({"path": self.rel(path), "error_code": code,
                                     "sha256": hashlib.sha256(body).hexdigest()})
        return self.rel(path)

    # --- one request -------------------------------------------------------
    def dispatch(self, board: Board, timeout: float):
        """(response, kind, detail). Every transport failure becomes a recorded kind."""
        try:
            return self.io.send(self.transport, "GET", board.url, timeout), None, None
        except PolicyViolation:
            raise  # a policy refusal is loop-level, never a board outcome
        except TransportError as e:
            kind = e.kind if e.kind in self.error_policy else "TRANSPORT_EXCEPTION"
            return None, kind, e.detail
        except Exception as e:  # recorded as a board failure with its type; never turned into a value
            return None, "TRANSPORT_EXCEPTION", f"{type(e).__name__}: {e}"

    # --- one board ---------------------------------------------------------
    def process_board(self, board: Board) -> dict:
        attempt = 0
        while True:
            attempt += 1
            if self.requests_used >= self.budgets["max_requests"]:
                raise BudgetExceeded("max_requests")
            remaining = self.remaining_seconds()
            if remaining <= 0:
                raise BudgetExceeded("max_seconds")
            wanted = board.timeout if board.timeout is not None else cfg.REQUEST_TIMEOUT_SECONDS
            timeout = min(wanted, remaining)  # never longer than the budget left

            self.requests_used += 1
            resp, kind, detail = self.dispatch(board, timeout)
            http_status = resp.status if resp is not None else None
            raw_path = sha = None
            if resp is not None:
                raw_path, sha = self.save_raw(board, attempt, resp.body)
                kind = classify_status(resp.status)

            verdict = None
            malformed_path = None
            if resp is not None and kind is None:
                verdict = parse_board(board.provider, resp.body)
                if not verdict.ok:
                    kind = verdict.error_code
                    detail = verdict.detail
                    if kind == "PARSE_SCHEMA_MISMATCH" or verdict.observations.get("truncation") == "syntax":
                        malformed_path = self.save_malformed(board, attempt, resp.body, kind)

            line = dict(event="ATTEMPT", **board.label(), attempt=attempt, timeout_seconds=round(timeout, 6),
                        http_status=http_status, error_kind=kind, detail=detail,
                        observations=verdict.observations if verdict else {},
                        raw_path=raw_path, malformed_path=malformed_path)
            result = dict(index=board.index, **board.label(), attempts=attempt, http_status=http_status,
                          observations=verdict.observations if verdict else {}, response_sha256=sha,
                          cache_hit=False, diff=None)

            if kind is None:
                self.trace(**line, job_count=verdict.job_count, error_code=None, decision="VERIFIED",
                           budget_remaining=self.budget_remaining())
                return dict(result, outcome="verified", job_count=verdict.job_count, error_code=None,
                            job_ids=list(verdict.job_ids))

            rule = self.error_policy[kind]
            retries_used = attempt - 1
            if rule["retry"] and retries_used < rule["max_retries"]:
                # GATE.md 9.9: a single fixed wait. With max_retries = 1, retries_used is 0 here,
                # so this is exactly base_wait; the multiplier is left unchanged (no behavior change).
                wait = rule["base_wait"] * (2 ** retries_used)
                if wait >= self.remaining_seconds():
                    self.trace(**line, job_count=None, error_code=None, decision="RETRY_BLOCKED_BY_BUDGET",
                               wait_seconds=wait, budget_remaining=self.budget_remaining())
                    raise BudgetExceeded("max_seconds")
                self.trace(**line, job_count=None, error_code=None, decision="RETRY",
                           wait_seconds=wait, budget_remaining=self.budget_remaining())
                self.sleep(wait)
                continue

            self.trace(**line, job_count=None, error_code=rule["code"], decision="ADVANCE_TO_NEXT_BOARD",
                       budget_remaining=self.budget_remaining())
            return dict(result, outcome="failed", job_count=None, error_code=rule["code"], job_ids=None)

    def record_state(self, board: Board, result: dict, prior: dict) -> None:
        path = state_path(self.root, board.token)
        old = prior[board.token]
        current = result["job_ids"] if result["outcome"] == "verified" else None
        if current is not None:
            result["diff"] = diff_ids(old["active_job_ids"] if old else None, current)
        diff = result["diff"]
        entry = {
            "run_id": self.run_id,
            "timestamp": self.now_iso(),
            "status": result["outcome"],
            "job_count": result["job_count"],
            "error_code": result["error_code"],
            "http_status": result["http_status"],
            "response_sha256": result["response_sha256"],
            "observations": result["observations"],
            "diff": None if diff is None else {"added": len(diff["added"]), "removed": len(diff["removed"]),
                                                "unchanged": diff["unchanged"]},
        }
        new = next_state(old, token=board.token, provider=board.provider, entry=entry, current_ids=current)
        save_state(self.io, path, new)
        prior[board.token] = new
        result["state_path"] = self.rel(path)

    # --- the run -----------------------------------------------------------
    def execute(self) -> dict:
        check_error_policy(self.error_policy)
        self.boards = boards = load_boards(self.io, self.config_path)

        # Read every board's prior state before any network call, so a corrupt file stops the run early.
        prior: dict[str, dict | None] = {}
        for b in boards:
            if b.token not in prior:
                prior[b.token] = load_state(self.io, state_path(self.root, b.token))
                old = prior[b.token]
                if old is not None and (old["board_token"] != b.token or old["provider"] != b.provider):
                    raise StateError(f"state file for {b.token!r} belongs to "
                                     f"{old['provider']}/{old['board_token']}, not {b.provider}/{b.token}")

        self.trace_path = self.root / cfg.TRACES_DIR / f"trace_{self.run_id}.jsonl"
        self.io.make_dirs(self.trace_path.parent)
        self.io.create_new(self.trace_path, b"")  # never overwrite an existing trace
        self.trace_created = True
        self.raw_dir = self.root / cfg.RAW_DIR / self.run_id
        self.io.make_dirs(self.raw_dir)
        self.trace(event="RUN_START", config=self.rel(self.config_path), boards_queued=len(boards),
                   budgets=self.budgets)

        tripped = interrupted = None
        skipped: list[Board] = []
        for idx, board in enumerate(boards):
            if idx >= self.budgets["max_boards"]:
                tripped, skipped = "max_boards", boards[idx:]
                break
            if self.remaining_seconds() <= 0:
                tripped, skipped = "max_seconds", boards[idx:]
                break
            self.boards_started += 1

            if board.key in self.cache:
                earlier = self.cache[board.key]
                result = dict(earlier, index=board.index, deliberate=board.deliberate, attempts=0,
                              cache_hit=True, diff=None, state_path=None)
                self.trace(event="IDEMPOTENT_CACHE_HIT", **board.label(), attempt=None,
                           http_status=earlier["http_status"], error_kind=None,
                           job_count=earlier["job_count"], error_code=earlier["error_code"],
                           observations=earlier["observations"], reused_from_board_index=earlier["index"],
                           decision="REUSE_OBSERVATION", budget_remaining=self.budget_remaining())
                self.results.append(result)
                continue

            try:
                result = self.process_board(board)
            except BudgetExceeded as e:
                tripped, interrupted, skipped = e.limit, board, boards[idx + 1:]
                break
            self.record_state(board, result, prior)
            self.cache[board.key] = result
            self.results.append(result)

        if tripped is None and self.elapsed() > self.budgets["max_seconds"]:
            tripped = "max_seconds"  # the last response arrived after the limit
        if tripped:
            self.trace(event="BUDGET_EXCEEDED", limit=tripped,
                       interrupted_board=interrupted.token if interrupted else None,
                       skipped_boards=[b.token for b in skipped], decision="STOP_RUN",
                       budget_remaining=self.budget_remaining())

        all_verified = len(self.results) == len(boards) and all(r["outcome"] == "verified" for r in self.results)
        if tripped:
            status = "BUDGET_EXCEEDED"
        elif all_verified:
            status = "SUCCESS"
        else:
            status = "PARTIAL_SUCCESS"

        report = self.report(status, tripped, interrupted, skipped)
        self.trace(event="RUN_END", status=status, exit_code=report["exit_code"],
                   budget_remaining=self.budget_remaining())
        self.write_checkpoint(report)
        return report

    def report(self, status, tripped, interrupted, skipped, extra=None) -> dict:
        boards = [{k: v for k, v in r.items() if k != "job_ids"} for r in self.results]
        report = {
            "run_id": self.run_id,
            "status": status,
            "exit_code": cfg.EXIT_CODES[status],
            "config": self.rel(self.config_path),
            "trace": self.rel(self.trace_path) if self.trace_created else None,
            "checkpoint": None,
            "elapsed_seconds": round(self.elapsed(), 3),
            "budget": {
                "tripped": tripped,
                "requests_used": self.requests_used,
                "boards_processed": len(self.results),
                "boards_queued": len(self.boards),
                **{k: v for k, v in self.budgets.items()},
            },
            "boards": boards,
            "failed_boards": [{"board": r["board"], "provider": r["provider"], "error_code": r["error_code"],
                               "http_status": r["http_status"]} for r in boards if r["outcome"] != "verified"],
            "interrupted_board": interrupted.token if interrupted else None,
            "skipped_boards": [b.token for b in skipped],
            "raw_files": self.raw_files,
            "malformed_files": self.malformed_files,
        }
        if extra:
            report.update(extra)
        return report

    def write_checkpoint(self, report: dict) -> None:
        path = self.root / cfg.CHECKPOINT_PATH
        checkpoint = {
            "run_id": self.run_id,
            "status": report["status"],
            "exit_code": report["exit_code"],
            "trace": report["trace"],
            "completed_boards": [{"board": r["board"], "outcome": r["outcome"], "cache_hit": r["cache_hit"]}
                                 for r in report["boards"]],
            "interrupted_board": report["interrupted_board"],
            "unvisited_boards": report["skipped_boards"],
            "requests_used": report["budget"]["requests_used"],
            "elapsed_seconds": report["elapsed_seconds"],
            "budget_tripped": report["budget"]["tripped"],
        }
        self.io.make_dirs(path.parent)
        self.io.replace_atomic(path, (json.dumps(checkpoint, indent=2) + "\n").encode("utf-8"))
        report["checkpoint"] = self.rel(path)

    def fatal(self, exc: BaseException) -> dict:
        subsystem = {ConfigError: "config", StateError: "state", PolicyViolation: "security_policy"}.get(
            type(exc), "filesystem" if isinstance(exc, OSError) else "runtime")
        report = self.report("FATAL_SYSTEM_ERROR", None, None, [], extra={
            "error": {"type": type(exc).__name__, "message": str(exc), "subsystem": subsystem,
                      "traceback": traceback.format_exception(exc)},
        })
        # Only record into this run's own trace, and only once it exists (never an older file).
        if self.trace_created:
            notes = []
            try:
                self.trace(event="FATAL_SYSTEM_ERROR", subsystem=subsystem, error=f"{type(exc).__name__}: {exc}",
                           budget_remaining=self.budget_remaining())
            except Exception as e:
                notes.append(f"could not write trace line: {e!r}")
            try:
                self.write_checkpoint(report)
            except Exception as e:
                notes.append(f"could not write checkpoint: {e!r}")
            if notes:
                report["error"]["secondary_failures"] = notes
        return report


def run_agent(*, root: Path = cfg.PROJECT_ROOT, config_path=cfg.DEFAULT_CONFIG, transport=None,
              policy: SecurityPolicy | None = None, clock=time.monotonic, sleep=time.sleep, now_iso=_utc_iso,
              run_id: str | None = None, error_policy=cfg.ERROR_POLICY, budgets=cfg.BUDGETS) -> dict:
    root = Path(root).resolve()
    config_path = Path(config_path)
    if not config_path.is_absolute():
        config_path = root / config_path  # against the project root, never the current directory
    run = Run(root=root, config_path=config_path, transport=transport or RequestsTransport(),
              policy=policy or SecurityPolicy(), clock=clock, sleep=sleep, now_iso=now_iso,
              run_id=run_id or utc_timestamp(), error_policy=error_policy, budgets=budgets)
    try:
        return run.execute()
    except Exception as exc:  # loop-level only: board failures never reach here
        return run.fatal(exc)


class _ArgumentError(Exception):
    pass


class _Parser(argparse.ArgumentParser):
    def error(self, message):  # argparse would exit 2, which GATE.md reserves for PARTIAL_SUCCESS
        raise _ArgumentError(message)


def main(argv=None) -> int:
    parser = _Parser(prog="python -m src.loop", description="JS2 bounded job-board loop (contract: GATE.md)")
    parser.add_argument("--config", default=cfg.DEFAULT_CONFIG,
                        help="board config, relative to the project root (default: %(default)s)")
    try:
        args = parser.parse_args(argv)
    except _ArgumentError as e:
        print(f"argument error: {e}", file=sys.stderr)
        return cfg.EXIT_CODES["FATAL_SYSTEM_ERROR"]
    report = run_agent(config_path=args.config)
    print(json.dumps(report, indent=2))
    if report["status"] == "FATAL_SYSTEM_ERROR":
        print("".join(report["error"]["traceback"]), file=sys.stderr)
    return report["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
