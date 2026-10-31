"""Action-surface 2 ("file read"): judge posting 8335469 from a file, with a read-only tool set.

Writes evidence/surface_file_posting.json (the posting, unmodified from the live raw response)
and evidence/surface_file_prompt.txt, then runs `claude -p` in a fresh temp dir that contains
only a byte-identical copy of the posting file. Tools: Read only; dontAsk denies anything else;
--restricted, no MCP, no settings. Saves the full stream-json transcript to
evidence/surface_file_output.json.
"""

import hashlib
import json
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from agent.claude_judge import SYSTEM_PATH, judge_model

PID = 8335469
RAW = Path("evidence/raw/20261031T182100Z_live.json")
POSTING = Path("evidence/surface_file_posting.json")
CHAT_PROMPT = Path("evidence/surface_chat_prompt.txt")
PROMPT = Path("evidence/surface_file_prompt.txt")
OUT = Path("evidence/surface_file_output.json")
POSTING_BLOCK_START = "posting.id: "


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main():
    job = next(j for j in json.loads(RAW.read_text())["jobs"] if j["id"] == PID)
    POSTING.write_text(json.dumps(job, indent=2, ensure_ascii=False) + "\n")

    # Same text as the chat prompt, except the pasted posting fields become a file pointer.
    chat = CHAT_PROMPT.read_text()
    head = chat[:chat.index(POSTING_BLOCK_START)]
    PROMPT.write_text(head + f"The posting is the JSON file {POSTING.name} in the current "
                             "directory. Read it from there.\n")

    model, model_source = judge_model()
    cmd = ["claude", "-p", "--model", model, "--output-format", "stream-json", "--verbose",
           "--tools", "Read", "--allowedTools", "Read", "--permission-mode", "dontAsk",
           "--restricted", "--strict-mcp-config", "--setting-sources", "",
           "--no-session-persistence", "--system-prompt", SYSTEM_PATH.read_text()]
    with tempfile.TemporaryDirectory() as d:
        copy = Path(d) / POSTING.name
        shutil.copyfile(POSTING, copy)
        listing = sorted(p.name for p in Path(d).iterdir())
        started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        proc = subprocess.run(cmd, input=PROMPT.read_text(), capture_output=True, text=True,
                              cwd=d, timeout=300)
        copy_sha = sha(copy.read_bytes())
    events = [json.loads(l) for l in proc.stdout.splitlines() if l.strip()]
    tool_uses = [c for e in events if e.get("type") == "assistant"
                 for c in e["message"]["content"] if c.get("type") == "tool_use"]
    result = next((e for e in events if e.get("type") == "result"), {})
    OUT.write_text(json.dumps({
        "started_utc": started,
        "model_requested": model, "model_source": model_source,
        "model_reported": sorted(result.get("modelUsage", {})),
        "command": cmd[:-1] + [f"<contents of prompts/{SYSTEM_PATH.name}>"],
        "prompt_file": str(PROMPT), "system_prompt_file": SYSTEM_PATH.name,
        "temp_dir_listing": listing,
        "posting_sha256": sha(POSTING.read_bytes()), "temp_copy_sha256": copy_sha,
        "tool_uses": tool_uses,
        "permission_denials": result.get("permission_denials"),
        "num_turns": result.get("num_turns"),
        "returncode": proc.returncode, "stderr": proc.stderr,
        "result_text": result.get("result"),
        "events": events,
    }, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {POSTING}, {PROMPT}, {OUT}")
    print("tool_uses:", [(t["name"], t["input"]) for t in tool_uses])
    print("permission_denials:", result.get("permission_denials"), "turns:", result.get("num_turns"))
    print("model_reported:", sorted(result.get("modelUsage", {})))
    print("----- result text -----")
    print(result.get("result"))


if __name__ == "__main__":
    main()
