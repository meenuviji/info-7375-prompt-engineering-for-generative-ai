"""Test doubles: a fake clock, a recording sleep, and a scripted transport over fixtures.

Nothing here opens a socket. A request the test did not script raises UnscriptedRequest,
a BaseException, so it gets past the loop's error handling and fails the test loudly
instead of being recorded as a board failure.
"""

import json
import shutil
import tempfile
from pathlib import Path

from src import config as cfg
from src.fetch import Response, TransportError
from src.loop import run_agent

FIXTURES = Path(__file__).resolve().parent / "fixtures"
RUN_ID = "TESTRUN"


class UnscriptedRequest(BaseException):
    pass


def fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def url(provider: str, token: str) -> str:
    return cfg.PROVIDER_URLS[provider].format(token=token)


# --- scripted steps -----------------------------------------------------------------
def ok(name: str, latency: float = 0.05):
    return {"status": 200, "body": fixture(name), "latency": latency}


def status(code: int, body: bytes = b"", latency: float = 0.05):
    return {"status": code, "body": body, "latency": latency}


def timeout():
    return {"error": "TIMEOUT"}


def error(kind: str, latency: float = 0.05):
    return {"error": kind, "latency": latency}


def boom(exc: Exception, latency: float = 0.05):
    return {"raise": exc, "latency": latency}


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class RecordingSleep:
    def __init__(self, clock: FakeClock):
        self.clock = clock
        self.calls: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)
        self.clock.advance(seconds)


class ScriptedTransport:
    def __init__(self, clock: FakeClock, script: dict[str, list[dict]]):
        self.clock = clock
        self.script = {u: list(steps) for u, steps in script.items()}
        self.calls: list[tuple[str, float]] = []

    def get(self, request_url: str, timeout_seconds: float) -> Response:
        self.calls.append((request_url, timeout_seconds))
        steps = self.script.get(request_url)
        if not steps:
            raise UnscriptedRequest(request_url)
        step = steps.pop(0)
        if step.get("error") == "TIMEOUT" and "latency" not in step:
            self.clock.advance(timeout_seconds)  # a timeout takes the whole timeout
        else:
            self.clock.advance(step.get("latency", 0.05))
        if "error" in step:
            raise TransportError(step["error"], "scripted fixture failure")
        if "raise" in step:
            raise step["raise"]
        return Response(step["status"], step["body"], {})


class Sandbox:
    """A temporary project root holding a config. Removed after the test."""

    def __init__(self, boards: list[dict] | dict, name: str = "boards.json"):
        self.root = Path(tempfile.mkdtemp(prefix="js2-test-")).resolve()
        (self.root / "config").mkdir()
        self.config = f"config/{name}"
        payload = boards if isinstance(boards, dict) else {"boards": boards}
        (self.root / self.config).write_text(json.dumps(payload))
        self.clock = FakeClock()
        self.sleep = RecordingSleep(self.clock)
        self.transport = None

    def run(self, script: dict[str, list[dict]] | None = None, **kwargs) -> dict:
        self.clock.now = 0.0
        self.transport = ScriptedTransport(self.clock, script or {})
        kwargs.setdefault("run_id", RUN_ID)
        return run_agent(root=self.root, config_path=self.config, transport=self.transport,
                         clock=self.clock, sleep=self.sleep, now_iso=lambda: "2026-11-09T00:00:00+00:00",
                         **kwargs)

    def trace_lines(self, run_id: str = RUN_ID) -> list[dict]:
        path = self.root / cfg.TRACES_DIR / f"trace_{run_id}.jsonl"
        return [json.loads(line) for line in path.read_text().splitlines()]

    def state(self, token: str) -> dict:
        return json.loads((self.root / cfg.STATES_DIR / f"{token}.json").read_text())

    def state_file(self, token: str) -> Path:
        return self.root / cfg.STATES_DIR / f"{token}.json"

    def cleanup(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)


def gh(token: str, **extra) -> dict:
    return {"provider": "greenhouse", "token": token, **extra}


def lever(token: str, **extra) -> dict:
    return {"provider": "lever", "token": token, **extra}
