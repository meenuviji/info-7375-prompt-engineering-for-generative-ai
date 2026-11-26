"""Tests for the js3-filter MCP server, started as a subprocess through mcp_client's logic.
Transcripts go to pytest's tmp_path, never to transcripts/."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import mcp_client  # noqa: E402
import mcp_server  # noqa: E402
from src import filter_v3  # noqa: E402
from src.postings import load_postings  # noqa: E402


@pytest.fixture(scope="module")
def demo(tmp_path_factory):
    tdir = tmp_path_factory.mktemp("transcripts")
    exchanges, code, transcript = mcp_client.run_demo(str(tdir))
    return {label: reply for label, _, reply in exchanges}, code, transcript, tdir


def test_server_exits_cleanly(demo):
    _, code, transcript, tdir = demo
    assert code == 0 and transcript is not None and transcript.parent == tdir


def test_initialize_reply(demo):
    r = demo[0]["initialize"]
    assert r["id"] == 1 and "error" not in r
    assert r["result"] == {"protocolVersion": "2025-06-18", "capabilities": {"tools": {}},
                           "serverInfo": {"name": "js3-filter", "version": "1.0"}}


def test_initialized_notification_gets_no_reply(demo):
    assert demo[0]["notifications/initialized"] is None


def test_tools_list_offers_exactly_score_posting(demo):
    tools = demo[0]["tools/list"]["result"]["tools"]
    assert [t["name"] for t in tools] == ["score_posting"]
    schema = tools[0]["inputSchema"]
    assert schema["required"] == ["posting_id"] and schema["properties"]["posting_id"]["type"] == "string"


def test_valid_call_matches_filter_v3(demo):
    result = demo[0]["tools/call valid id"]["result"]
    assert result["isError"] is False
    sc = result["structuredContent"]
    assert json.loads(result["content"][0]["text"]) == sc
    p = next(p for p in load_postings()[0] if p.id == mcp_client.VALID_POSTING_ID)
    expected = filter_v3.evaluate(p.title, p.location, p.description)
    assert (sc["decision"], sc["score"], sc["rules_fired"], sc["close_call"]) == \
           (expected.decision, expected.score, list(expected.rules_fired), expected.close_call)
    assert sc["rule_set"] == "v3" and sc["filter_md_version"] == "v1 (2026-11-25)"


def test_unknown_posting_id_is_tool_error_not_path(demo):
    r = demo[0]["tools/call unknown id"]
    assert "error" not in r and r["result"]["isError"] is True
    assert "unknown posting_id" in r["result"]["content"][0]["text"]


def test_undeclared_tool_is_jsonrpc_error(demo):
    r = demo[0]["tools/call undeclared tool"]
    assert r["id"] == 5 and r["error"]["code"] == -32602 and "Unknown tool" in r["error"]["message"]


def test_transcript_has_both_directions_and_every_line(demo):
    _, _, transcript, _ = demo
    entries = [json.loads(line) for line in transcript.read_text().splitlines()]
    received = [e for e in entries if e["direction"] == "client->server"]
    sent = [e for e in entries if e["direction"] == "server->client"]
    assert len(received) == len(mcp_client.DEMO) == 6
    assert len(sent) == 5  # every request answered, the notification not
    assert {e["direction"] for e in entries} == {"client->server", "server->client"}
    assert all(e["ts"].endswith("Z") for e in entries)
    assert json.loads(received[1]["line"])["method"] == "notifications/initialized"


def test_other_methods_and_malformed_lines(tmp_path):
    client = mcp_client.StdioClient(str(tmp_path))
    try:
        assert client.send({"jsonrpc": "2.0", "id": 7, "method": "resources/list"})["error"]["code"] == -32601
        client.send_raw("{not json")
        assert client.read()["error"]["code"] == -32700
        client.send_raw("[]")
        assert client.read()["error"]["code"] == -32600
        bad_args = {"jsonrpc": "2.0", "id": 8, "method": "tools/call",
                    "params": {"name": "score_posting", "arguments": {"posting_id": 8275927}}}
        assert client.send(bad_args)["error"]["code"] == -32602
        assert client.send({"jsonrpc": "2.0", "method": "notifications/cancelled"}) is None
        assert client.send({"jsonrpc": "2.0", "id": 9, "method": "tools/list"})["id"] == 9  # still in sync
    finally:
        code, _ = client.close()
    assert code == 0


def test_each_start_gets_a_new_transcript(tmp_path):
    a = mcp_server.Transcript(tmp_path)
    b = mcp_server.Transcript(tmp_path)
    a.close(), b.close()
    assert a.path != b.path and len(list(tmp_path.iterdir())) == 2


def test_refuses_to_score_when_filter_md_changed():
    server = mcp_server.Server(expected_sha256="0" * 64)
    reply = server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                           "params": {"name": "score_posting", "arguments": {"posting_id": "8275927"}}})
    assert reply["result"]["isError"] is True and "FILTER.md has changed" in reply["result"]["content"][0]["text"]
