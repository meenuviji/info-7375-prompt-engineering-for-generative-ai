"""Minimal MCP client for js3-filter: starts mcp_server.py as a subprocess over stdio.

Usage: .venv/bin/python mcp_client.py

Sends, one JSON line each: initialize, notifications/initialized, tools/list, a valid
tools/call, a tools/call with an unknown posting id, and a call to an undeclared tool.
Prints each reply. Requests are answered one line each; the notification gets no reply.
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VALID_POSTING_ID = "8275927"          # cloudflare "Data Scientist"
UNKNOWN_POSTING_ID = "../../etc/passwd"  # not a loaded id; shows the id is never used as a path

DEMO = [
    ("initialize", {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                    "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                               "clientInfo": {"name": "js3-minimal-client", "version": "1.0"}}}),
    ("notifications/initialized", {"jsonrpc": "2.0", "method": "notifications/initialized"}),
    ("tools/list", {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}),
    ("tools/call valid id", {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                             "params": {"name": "score_posting", "arguments": {"posting_id": VALID_POSTING_ID}}}),
    ("tools/call unknown id", {"jsonrpc": "2.0", "id": 4, "method": "tools/call",
                               "params": {"name": "score_posting",
                                          "arguments": {"posting_id": UNKNOWN_POSTING_ID}}}),
    ("tools/call undeclared tool", {"jsonrpc": "2.0", "id": 5, "method": "tools/call",
                                    "params": {"name": "delete_posting", "arguments": {"posting_id": "1"}}}),
]


class StdioClient:
    def __init__(self, transcript_dir: str | None = None):
        cmd = [sys.executable, str(ROOT / "mcp_server.py")]
        if transcript_dir:
            cmd += ["--transcript-dir", str(transcript_dir)]
        self.proc = subprocess.Popen(cmd, cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, text=True, encoding="utf-8")

    def send(self, message: dict):
        """Send one message. Requests (with "id") return the parsed reply; notifications None."""
        self.send_raw(json.dumps(message))
        if "id" not in message:
            return None
        return self.read()

    def send_raw(self, line: str) -> None:
        self.proc.stdin.write(line + "\n")
        self.proc.stdin.flush()

    def read(self) -> dict:
        line = self.proc.stdout.readline()
        if not line:
            raise RuntimeError(f"server closed stdout; stderr: {self.proc.stderr.read()}")
        return json.loads(line)

    def close(self) -> tuple[int, str]:
        """Close stdin, wait for exit; return (exit code, stderr text)."""
        self.proc.stdin.close()
        rest = self.proc.stdout.read()
        if rest.strip():
            raise RuntimeError(f"unexpected extra server output: {rest!r}")
        code = self.proc.wait(timeout=30)
        return code, self.proc.stderr.read()


def transcript_path(stderr: str) -> Path | None:
    for line in stderr.splitlines():
        if line.startswith("js3-filter: transcript "):
            return Path(line.split("js3-filter: transcript ", 1)[1].strip())
    return None


def run_demo(transcript_dir: str | None = None):
    """Run the six-message demo. Returns (list of (label, request, reply), exit code, transcript path)."""
    client = StdioClient(transcript_dir)
    exchanges = []
    try:
        for label, message in DEMO:
            exchanges.append((label, message, client.send(message)))
    finally:
        code, stderr = client.close()
    return exchanges, code, transcript_path(stderr)


def main() -> int:
    exchanges, code, transcript = run_demo()
    for label, request, reply in exchanges:
        print(f"--- {label}")
        print(f"  sent:  {json.dumps(request)}")
        print(f"  reply: {json.dumps(reply, indent=2) if reply is not None else '(none: notification)'}")
    print(f"--- server exit code {code}; transcript {transcript}")
    return 0 if code == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
