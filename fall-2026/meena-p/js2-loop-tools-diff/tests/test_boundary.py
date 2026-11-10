"""Permission boundary tests: one per row of BOUNDARY_TESTS.md (row 15 is reserved).

Each test asserts the Predicted column exactly as written before the policy existed
(commit fd0e047). Rows 1-14 call the policy directly inside a temporary project root;
nothing is written and nothing touches the network. Rows 16 and 17 run the loop with
the scripted transport.
"""

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from types import MappingProxyType
from unittest import mock

from src import config as cfg
from src import loop
from src.policy import PolicyViolation, SecurityPolicy
from tests.helpers import Sandbox, gh, lever, ok, url

GREENHOUSE_CF = "https://boards-api.greenhouse.io/v1/boards/cloudflare/jobs"
LEVER_PALANTIR = "https://api.lever.co/v0/postings/palantir?mode=json"


class BoundaryTest(unittest.TestCase):
    def setUp(self):
        self.sb = Sandbox([gh("cloudflare")])  # temporary root with config/boards.json
        self.root = self.sb.root
        self.policy = SecurityPolicy(self.root)
        self.approved = SecurityPolicy(self.root, approve_config_write=True)

    def tearDown(self):
        self.sb.cleanup()

    def assertAllowed(self, check, *args):
        try:
            check(*args)
        except PolicyViolation as e:  # pragma: no cover - only reached on failure
            self.fail(f"expected ALLOW, got DENY by {e.rule}: {e}")

    def assertDenied(self, rule, check, *args):
        with self.assertRaises(PolicyViolation) as caught:
            check(*args)
        self.assertEqual(caught.exception.rule, rule)


class NetworkBoundaries(BoundaryTest):
    def test_boundary_01_allowed_host(self):
        # ALLOW — HTTPS GET to an approved Greenhouse host
        self.assertAllowed(self.policy.validate_network_request, "GET", GREENHOUSE_CF)

    def test_boundary_02_second_allowed_host(self):
        # ALLOW — HTTPS GET to an approved Lever host
        self.assertAllowed(self.policy.validate_network_request, "GET", LEVER_PALANTIR)

    def test_boundary_03_host_off_allow_list(self):
        # DENY — example.com is not an approved host
        self.assertDenied("net.host-not-allowed", self.policy.validate_network_request,
                          "GET", "https://example.com/jobs")

    def test_boundary_04_lookalike_host(self):
        # DENY — the hostname is not an exact match
        self.assertDenied("net.host-not-allowed", self.policy.validate_network_request,
                          "GET", "https://boards-api.greenhouse.io.evil.com/jobs")

    def test_boundary_05_non_https(self):
        # DENY — only HTTPS requests are permitted
        self.assertDenied("net.scheme-not-https", self.policy.validate_network_request,
                          "GET", "http://boards-api.greenhouse.io/v1/boards/cloudflare/jobs")

    def test_boundary_14_non_get_request(self):
        # DENY — POST requests are not permitted
        self.assertDenied("net.method-not-get", self.policy.validate_network_request, "POST", GREENHOUSE_CF)


class FileBoundaries(BoundaryTest):
    def test_boundary_06_write_inside_allowed_folder(self):
        # ALLOW — the file is inside output/
        self.assertAllowed(self.policy.validate_file_write, "output/raw/test.json")

    def test_boundary_07_path_traversal(self):
        # DENY — the resolved path escapes output/
        self.assertDenied("file.write-outside-allowed-folders", self.policy.validate_file_write,
                          "output/../GATE.md")

    def test_boundary_08_prefix_trick(self):
        # DENY — output-evil/ is not the same as output/
        self.assertDenied("file.write-outside-allowed-folders", self.policy.validate_file_write,
                          "output-evil/x.json")

    def test_boundary_09_symlink_escape(self):
        # DENY — the symlink resolves outside the allowed folder
        (self.root / "output").mkdir()
        os.symlink("/tmp", self.root / "output" / "link")
        self.assertDenied("file.write-outside-allowed-folders", self.policy.validate_file_write,
                          "output/link/x.json")

    def test_boundary_10_read_vs_write_same_file(self):
        # ALLOW read, DENY write — reading config is permitted, but writing requires approval
        self.assertAllowed(self.policy.validate_file_read, "config/boards.json")
        self.assertDenied("file.config-write-needs-approval", self.policy.validate_file_write,
                          "config/boards.json")

    def test_boundary_11_approval_required_write_without_approval(self):
        # DENY — the required approval flag is missing
        self.assertDenied("file.config-write-needs-approval", self.policy.validate_file_write,
                          "config/boards.json")

    def test_boundary_12_approval_required_write_with_approval(self):
        # ALLOW — the approval flag permits writing to config/
        self.assertAllowed(self.approved.validate_file_write, "config/boards.json")
        # and the CLI flag is what grants it
        with mock.patch.object(loop, "run_agent", return_value={"status": "SUCCESS", "exit_code": 0}) as run:
            self.assertEqual(loop.main(["--approve-config-write"]), 0)
        self.assertTrue(run.call_args.kwargs["approve_config_write"])
        with mock.patch.object(loop, "run_agent", return_value={"status": "SUCCESS", "exit_code": 0}) as run:
            loop.main([])
        self.assertFalse(run.call_args.kwargs["approve_config_write"])

    def test_boundary_13_outside_write_even_with_approval(self):
        # DENY — approval does not override path restrictions
        self.assertDenied("file.write-outside-allowed-folders", self.approved.validate_file_write, "/tmp/x.json")


class LoopBoundaries(BoundaryTest):
    def test_boundary_16_config_path_outside_config(self):
        # DENY — the config file is outside the permitted directory
        outside = Path(tempfile.mkdtemp(prefix="js2-boundary-16-", dir="/tmp"))
        try:
            boards = outside / "boards.json"
            boards.write_text(json.dumps({"boards": [gh("cloudflare")]}))  # a valid config, so only the path is wrong
            self.sb.config = str(boards)
            report = self.sb.run({})
        finally:
            shutil.rmtree(outside, ignore_errors=True)
        self.assertEqual((report["status"], report["exit_code"]), ("FATAL_SYSTEM_ERROR", 1))
        self.assertEqual(report["error"]["subsystem"], "security_policy")
        self.assertEqual(report["error"]["denied_rule"], "file.config-path-outside-config")
        self.assertEqual(self.sb.transport.calls, [])
        self.assertFalse((self.root / "traces").exists())  # denied before a trace exists: report only

    def test_boundary_17_board_on_disallowed_host_in_config(self):
        # DENY — a URL in config must still satisfy the host allow-list.
        # The config schema builds every URL from a provider template, so the test adds a
        # template that points at example.com and lists one board under it.
        self.sb.cleanup()
        self.sb = Sandbox([gh("cloudflare"), {"provider": "example", "token": "badboard"}, lever("palantir")])
        templates = MappingProxyType({**cfg.PROVIDER_URLS, "example": "https://example.com/boards/{token}/jobs"})
        script = {url("greenhouse", "cloudflare"): [ok("greenhouse_three_jobs.json")],
                  url("lever", "palantir"): [ok("lever_two_jobs.json")]}
        with mock.patch.object(cfg, "PROVIDER_URLS", templates):
            report = self.sb.run(script)

        bad = next(b for b in report["boards"] if b["board"] == "badboard")
        self.assertEqual(bad["error_code"], "POLICY_DENIED")
        self.assertIsNone(bad["job_count"])

        # Row 17 outcome: no request is sent, the run continues to the other boards,
        # ending PARTIAL_SUCCESS (exit 2).
        self.assertTrue(all("example.com" not in u for u, _ in self.sb.transport.calls))
        self.assertEqual(report["budget"]["requests_used"], 2)
        self.assertEqual([b["outcome"] for b in report["boards"]], ["verified", "failed", "verified"])
        self.assertEqual((report["status"], report["exit_code"]), ("PARTIAL_SUCCESS", 2))

        # The denial is in the trace with the rule that denied it; the state is a failed entry.
        (line,) = [l for l in self.sb.trace_lines() if l.get("board") == "badboard"]
        self.assertEqual((line["request_sent"], line["denied_rule"]), (False, "net.host-not-allowed"))
        state = self.sb.state("badboard")
        self.assertIsNone(state["active_job_ids"])
        self.assertEqual(state["ledger"][-1]["error_code"], "POLICY_DENIED")


if __name__ == "__main__":
    unittest.main()
