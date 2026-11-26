"""js3-filter: a Model Context Protocol tool server, standard library only (no MCP SDK).

Transport: JSON-RPC 2.0 over stdio, one JSON message per line (stdout carries only
JSON-RPC; diagnostics go to stderr).

Methods: initialize, notifications/initialized (no reply), tools/list, tools/call.
Any other request gets JSON-RPC error -32601; other notifications are ignored (JSON-RPC
never replies to notifications). Batches (JSON arrays) are refused with -32600.

One tool, score_posting {"posting_id": string}: looks the id up among the postings loaded
from data/raw/ by src/postings.py and returns decision, score, rules_fired and close_call
from rule set v3 (src/filter_v3.py = FILTER.md as committed in 4923b21). If FILTER.md's
sha256 differs from config.V3_FILTER_MD_SHA256, the tool refuses to score (isError) rather
than report a version FILTER.md no longer describes.

Errors: unknown tool or bad arguments -> JSON-RPC -32602; unknown posting id -> a normal
result with isError true (MCP reports tool execution errors inside the result).

Read-only: no network; the only file written is this run's transcript,
transcripts/mcp_<UTC timestamp>.jsonl, created with mode "x" (never overwritten). The
posting_id is compared against loaded ids only; it is never used to build a path.

Usage: .venv/bin/python mcp_server.py [--transcript-dir DIR]   (default: transcripts/)
"""

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from src import config as cfg
from src import filter_v3
from src.postings import load_postings

SERVER_INFO = {"name": "js3-filter", "version": "1.0"}
SUPPORTED_PROTOCOLS = ("2025-06-18", "2025-03-26", "2024-11-05")
DEFAULT_PROTOCOL = SUPPORTED_PROTOCOLS[0]
MAX_ID_LENGTH = 200

PARSE_ERROR, INVALID_REQUEST, METHOD_NOT_FOUND, INVALID_PARAMS, INTERNAL_ERROR = -32700, -32600, -32601, -32602, -32603

SCORE_POSTING = {
    "name": "score_posting",
    "title": "Score a job posting",
    "description": ("Score one posting from the JS3 data snapshot (cloudflare, datadog, palantir) with the "
                    "FILTER.md rules. Returns decision (KEPT/REJECTED/CANNOT_TELL), score, rules_fired and "
                    "close_call. Read-only."),
    "inputSchema": {
        "type": "object",
        "properties": {"posting_id": {"type": "string", "description": "Greenhouse or Lever posting id"}},
        "required": ["posting_id"],
        "additionalProperties": False,
    },
}
TOOLS = {SCORE_POSTING["name"]: SCORE_POSTING}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Transcript:
    """Append-only JSONL log of every line in and out. A new file per server start."""

    def __init__(self, directory: Path):
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / f"mcp_{utc_now().strftime('%Y%m%dT%H%M%S%fZ')}.jsonl"
        self._f = open(self.path, "x", encoding="utf-8")  # "x": fails rather than overwrite

    def log(self, direction: str, line: str) -> None:
        entry = {"ts": utc_now().isoformat(timespec="microseconds").replace("+00:00", "Z"),
                 "direction": direction, "line": line}
        self._f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self._f.flush()

    def close(self) -> None:
        self._f.close()


class ToolError(Exception):
    """A tool execution error: reported as a result with isError true."""


class Server:
    def __init__(self, filter_md_path: Path | None = None, expected_sha256: str = cfg.V3_FILTER_MD_SHA256):
        self.filter_md_path = filter_md_path or cfg.PROJECT_ROOT / "FILTER.md"
        self.expected_sha256 = expected_sha256
        self._by_id = None

    # --- data ----------------------------------------------------------------------------------
    def _postings(self) -> dict:
        if self._by_id is None:
            by_id: dict[str, list] = {}
            for p in load_postings(keep_missing_title=True)[0]:
                by_id.setdefault(p.id, []).append(p)
            self._by_id = by_id
        return self._by_id

    def _filter_md(self) -> tuple[str, str]:
        data = self.filter_md_path.read_bytes()
        m = re.search(rb"^Version:\s*(.+)$", data, re.MULTILINE)
        return hashlib.sha256(data).hexdigest(), (m.group(1).decode().strip() if m else "unknown")

    # --- tool ----------------------------------------------------------------------------------
    def score_posting(self, posting_id: str) -> dict:
        sha, md_version = self._filter_md()
        if sha != self.expected_sha256:
            raise ToolError("FILTER.md has changed since rule set v3 was implemented "
                            f"(sha256 {sha[:12]}..., expected {self.expected_sha256[:12]}...); "
                            "refusing to score with rules FILTER.md may no longer describe")
        matches = self._postings().get(posting_id, [])
        if not matches:
            raise ToolError(f"unknown posting_id {posting_id!r}: not in data/raw/")
        if len(matches) > 1:
            raise ToolError(f"posting_id {posting_id!r} is ambiguous across providers")
        p = matches[0]
        r = filter_v3.evaluate(p.title, p.location, p.description)
        return {"posting_id": p.id, "provider": p.provider, "board": p.board, "title": p.title,
                "decision": r.decision, "score": r.score, "rules_fired": list(r.rules_fired),
                "close_call": r.close_call, "rule_set": "v3",
                "filter_md_version": md_version, "filter_md_sha256": sha}

    # --- JSON-RPC --------------------------------------------------------------------------------
    def _tools_call(self, params) -> dict:
        if not isinstance(params, dict) or not isinstance(params.get("name"), str):
            raise _RpcError(INVALID_PARAMS, "tools/call needs params.name (string)")
        name = params["name"]
        if name not in TOOLS:
            raise _RpcError(INVALID_PARAMS, f"Unknown tool: {name}")
        args = params.get("arguments", {})
        if not isinstance(args, dict) or set(args) != {"posting_id"} or not isinstance(args["posting_id"], str):
            raise _RpcError(INVALID_PARAMS, 'arguments must be exactly {"posting_id": string}')
        if not args["posting_id"] or len(args["posting_id"]) > MAX_ID_LENGTH:
            raise _RpcError(INVALID_PARAMS, f"posting_id must be 1-{MAX_ID_LENGTH} characters")
        try:
            result = self.score_posting(args["posting_id"])
        except ToolError as e:
            return {"content": [{"type": "text", "text": str(e)}], "isError": True}
        return {"content": [{"type": "text", "text": json.dumps(result)}],
                "structuredContent": result, "isError": False}

    def handle(self, message):
        """One parsed message -> a reply dict, or None (notifications)."""
        if not isinstance(message, dict):
            return _error(None, INVALID_REQUEST, "expected a single JSON-RPC object (batches not supported)")
        msg_id = message.get("id")
        is_notification = "id" not in message
        if message.get("jsonrpc") != "2.0" or not isinstance(message.get("method"), str):
            return None if is_notification else _error(msg_id, INVALID_REQUEST, "not a JSON-RPC 2.0 request")
        method, params = message["method"], message.get("params", {})
        if is_notification:
            return None  # notifications/initialized and any other notification: never answered
        try:
            if method == "initialize":
                requested = params.get("protocolVersion") if isinstance(params, dict) else None
                version = requested if requested in SUPPORTED_PROTOCOLS else DEFAULT_PROTOCOL
                return _result(msg_id, {"protocolVersion": version, "capabilities": {"tools": {}},
                                        "serverInfo": SERVER_INFO})
            if method == "tools/list":
                return _result(msg_id, {"tools": list(TOOLS.values())})
            if method == "tools/call":
                return _result(msg_id, self._tools_call(params))
            raise _RpcError(METHOD_NOT_FOUND, f"Method not found: {method}")
        except _RpcError as e:
            return _error(msg_id, e.code, e.message)
        except Exception as e:  # never crash the loop on one bad message
            return _error(msg_id, INTERNAL_ERROR, f"internal error: {type(e).__name__}")

    def handle_line(self, line: str):
        try:
            message = json.loads(line)
        except json.JSONDecodeError as e:
            return _error(None, PARSE_ERROR, f"Parse error: {e.msg}")
        return self.handle(message)


class _RpcError(Exception):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code, self.message = code, message


def _result(msg_id, result) -> dict:
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def _error(msg_id, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}


def serve(stdin, stdout, transcript: Transcript, server: Server) -> None:
    for raw in stdin:
        line = raw.rstrip("\r\n")
        transcript.log("client->server", line)
        if not line.strip():
            continue
        reply = server.handle_line(line)
        if reply is not None:
            out = json.dumps(reply, ensure_ascii=False)
            stdout.write(out + "\n")
            stdout.flush()
            transcript.log("server->client", out)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="js3-filter MCP server (stdio)")
    parser.add_argument("--transcript-dir", default=str(cfg.PROJECT_ROOT / "transcripts"))
    args = parser.parse_args(argv)
    transcript = Transcript(Path(args.transcript_dir))
    print(f"js3-filter: transcript {transcript.path}", file=sys.stderr, flush=True)
    try:
        serve(sys.stdin, sys.stdout, transcript, Server())
    finally:
        transcript.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
