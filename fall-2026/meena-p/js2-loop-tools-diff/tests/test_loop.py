"""The loop: exit statuses, budgets, repeat rule, error policy, state, files, I/O routing.

Every test runs in a temporary project root with a scripted transport over hand-written
fixtures. No test touches the network or the real project folders.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path

from src import config as cfg
from src.loop import Board, main
from src.policy import PolicyViolation, SecurityPolicy
from tests.helpers import (Sandbox, boom, error, fixture, gh, lever, ok, status, timeout, url)

CF, DD, AU = url("greenhouse", "cloudflare"), url("greenhouse", "datadog"), url("lever", "automattic")
REAL = [gh("cloudflare"), gh("datadog"), lever("automattic")]
REAL_OK = {CF: [ok("greenhouse_three_jobs.json")], DD: [ok("greenhouse_minified_one_job.json")],
           AU: [ok("lever_two_jobs.json")]}


def by_board(report):
    return {b["board"]: b for b in report["boards"]}


class SandboxTest(unittest.TestCase):
    boards = REAL

    def setUp(self):
        self.sb = Sandbox(self.boards)

    def tearDown(self):
        self.sb.cleanup()

    def attempts(self):
        return [line for line in self.sb.trace_lines() if line["event"] == "ATTEMPT"]


# ============================================================ exit statuses
class ExitStatuses(SandboxTest):
    def test_success_exit_0(self):
        report = self.sb.run(REAL_OK)
        self.assertEqual((report["status"], report["exit_code"]), ("SUCCESS", 0))
        self.assertEqual([b["job_count"] for b in report["boards"]], [3, 1, 2])
        self.assertEqual(len(report["raw_files"]), 3)
        for f in report["raw_files"]:
            self.assertEqual(len(f["sha256"]), 64)
            self.assertTrue((self.sb.root / f["path"]).is_file())

    def test_partial_success_exit_2_and_later_boards_still_run(self):
        script = dict(REAL_OK, **{CF: [status(404)]})  # first board fails
        report = self.sb.run(script)
        self.assertEqual((report["status"], report["exit_code"]), ("PARTIAL_SUCCESS", 2))
        boards = by_board(report)
        self.assertEqual(boards["cloudflare"]["error_code"], "BOARD_NOT_FOUND")
        self.assertEqual(boards["datadog"]["outcome"], "verified")
        self.assertEqual(boards["automattic"]["outcome"], "verified")

    def test_budget_exceeded_exit_3(self):
        report = self.sb.run(REAL_OK, budgets=dict(cfg.BUDGETS, max_requests=2))
        self.assertEqual((report["status"], report["exit_code"]), ("BUDGET_EXCEEDED", 3))
        self.assertEqual(report["budget"]["tripped"], "max_requests")
        self.assertEqual(report["skipped_boards"], [])
        self.assertEqual(report["interrupted_board"], "automattic")

    def test_fatal_exit_1_on_missing_config(self):
        (self.sb.root / self.sb.config).unlink()
        report = self.sb.run({})
        self.assertEqual((report["status"], report["exit_code"]), ("FATAL_SYSTEM_ERROR", 1))
        self.assertEqual(report["error"]["subsystem"], "config")
        self.assertTrue(report["error"]["traceback"])
        self.assertEqual(self.sb.transport.calls, [])
        self.assertFalse((self.sb.root / "traces").exists())

    def test_fatal_exit_1_on_corrupt_config(self):
        (self.sb.root / self.sb.config).write_text('{"boards": [')
        self.assertEqual(self.sb.run({})["exit_code"], 1)

    def test_fatal_exit_1_on_unknown_provider(self):
        (self.sb.root / self.sb.config).write_text(json.dumps({"boards": [{"provider": "workday", "token": "x"}]}))
        self.assertEqual(self.sb.run({})["exit_code"], 1)

    def test_fatal_exit_1_on_corrupt_state_before_any_request(self):
        path = self.sb.state_file("datadog")
        path.parent.mkdir(parents=True)
        path.write_text("{not json")
        report = self.sb.run(REAL_OK)
        self.assertEqual(report["exit_code"], 1)
        self.assertEqual(report["error"]["subsystem"], "state")
        self.assertEqual(self.sb.transport.calls, [])

    def test_fatal_exit_1_on_missing_error_policy_row(self):
        policy = {k: v for k, v in cfg.ERROR_POLICY.items() if k != "HTTP_404"}
        report = self.sb.run(REAL_OK, error_policy=policy)
        self.assertEqual(report["exit_code"], 1)
        self.assertIn("HTTP_404", report["error"]["message"])
        self.assertEqual(self.sb.transport.calls, [])

    def test_fatal_exit_1_when_a_policy_validator_refuses(self):
        class Refuse(SecurityPolicy):
            def validate_network_request(self, method, u):
                raise PolicyViolation("refused for test")

        report = self.sb.run(REAL_OK, policy=Refuse())
        self.assertEqual(report["exit_code"], 1)
        self.assertEqual(report["error"]["subsystem"], "security_policy")
        self.assertEqual(self.sb.transport.calls, [])

    def test_cli_argument_error_exits_1_not_argparse_2(self):
        self.assertEqual(main(["--no-such-flag"]), 1)


class DeliberateFlag(SandboxTest):
    boards = REAL + [gh("fail-timeout", deliberate=True, timeout=0.001)]

    def test_deliberate_failure_still_makes_the_run_partial(self):
        script = dict(REAL_OK, **{url("greenhouse", "fail-timeout"): [timeout(), timeout()]})
        report = self.sb.run(script)
        self.assertEqual((report["status"], report["exit_code"]), ("PARTIAL_SUCCESS", 2))
        board = by_board(report)["fail-timeout"]
        self.assertTrue(board["deliberate"])
        self.assertEqual(board["error_code"], "TIMEOUT_EXHAUSTED")
        self.assertTrue(all(line["deliberate"] for line in self.attempts() if line["board"] == "fail-timeout"))
        # the board's own timeout is used, not 10 s
        self.assertEqual([t for u, t in self.sb.transport.calls if "fail-timeout" in u], [0.001, 0.001])

    def test_deliberate_board_that_succeeds_does_not_change_status_either(self):
        script = dict(REAL_OK, **{url("greenhouse", "fail-timeout"): [ok("greenhouse_three_jobs.json")]})
        self.assertEqual(self.sb.run(script)["status"], "SUCCESS")


class ShippedConfigs(unittest.TestCase):
    def test_both_configs_load_and_fit_max_boards(self):
        from src.loop import load_boards
        from src.policy import GuardedIO
        io = GuardedIO(SecurityPolicy())
        real = load_boards(io, cfg.PROJECT_ROOT / "config/boards.json")
        full = load_boards(io, cfg.PROJECT_ROOT / "config/boards_with_failures.json")
        self.assertFalse(any(b.deliberate for b in real))
        self.assertEqual(len(full), cfg.MAX_BOARDS)
        self.assertEqual({b.token for b in full if b.deliberate}, {"empty-verified", "fail-timeout"})
        self.assertEqual(next(b.timeout for b in full if b.token == "fail-timeout"), 0.001)


# ============================================================ budgets
class Budgets(SandboxTest):
    def test_max_boards_skips_the_rest(self):
        self.sb.cleanup()
        tokens = ["b1", "b2", "b3", "b4", "b5", "b6"]
        self.sb = Sandbox([gh(t) for t in tokens])
        script = {url("greenhouse", t): [ok("greenhouse_three_jobs.json")] for t in tokens}
        report = self.sb.run(script)
        self.assertEqual(report["budget"]["tripped"], "max_boards")
        self.assertEqual(report["skipped_boards"], ["b6"])
        self.assertEqual(len(self.sb.transport.calls), 5)
        self.assertFalse(self.sb.state_file("b6").exists())

    def test_max_requests_stops_before_the_next_request(self):
        report = self.sb.run(REAL_OK, budgets=dict(cfg.BUDGETS, max_requests=1))
        self.assertEqual(report["budget"]["tripped"], "max_requests")
        self.assertEqual(report["budget"]["requests_used"], 1)
        self.assertEqual(len(self.sb.transport.calls), 1)
        self.assertEqual(report["skipped_boards"], ["automattic"])

    def test_exactly_max_requests_is_not_exceeded(self):
        report = self.sb.run(REAL_OK, budgets=dict(cfg.BUDGETS, max_requests=3))
        self.assertEqual(report["status"], "SUCCESS")

    def test_max_seconds_caps_the_request_timeout_at_the_time_left(self):
        script = {CF: [ok("greenhouse_three_jobs.json", latency=25)], DD: [ok("greenhouse_three_jobs.json", latency=29)],
                  AU: [ok("lever_two_jobs.json", latency=1)]}
        report = self.sb.run(script)
        timeouts = [t for _, t in self.sb.transport.calls]
        self.assertEqual(timeouts[:2], [10.0, 10.0])
        self.assertAlmostEqual(timeouts[2], 6.0)  # 60 - 54 s left, less than 10 s
        self.assertEqual(report["status"], "SUCCESS")

    def test_max_seconds_never_starts_a_request_with_no_time_left(self):
        script = {CF: [ok("greenhouse_three_jobs.json", latency=61)]}
        report = self.sb.run(script)
        self.assertEqual(report["budget"]["tripped"], "max_seconds")
        self.assertEqual(len(self.sb.transport.calls), 1)
        self.assertEqual(report["skipped_boards"], ["datadog", "automattic"])
        self.assertEqual(by_board(report)["cloudflare"]["outcome"], "verified")  # it did arrive

    def test_backoff_that_would_pass_max_seconds_stops_the_run(self):
        script = {CF: [status(503, latency=58.5)]}  # 1.5 s left, 2.0 s wait needed
        report = self.sb.run(script)
        self.assertEqual(report["budget"]["tripped"], "max_seconds")
        self.assertEqual(report["interrupted_board"], "cloudflare")
        self.assertEqual(self.sb.sleep.calls, [])
        self.assertEqual(self.attempts()[-1]["decision"], "RETRY_BLOCKED_BY_BUDGET")
        self.assertFalse(self.sb.state_file("cloudflare").exists())  # interrupted: no state write

    def test_budget_state_written_to_checkpoint(self):
        self.sb.run(REAL_OK, budgets=dict(cfg.BUDGETS, max_requests=1))
        cp = json.loads((self.sb.root / cfg.CHECKPOINT_PATH).read_text())
        self.assertEqual(cp["budget_tripped"], "max_requests")
        self.assertEqual(cp["interrupted_board"], "datadog")
        self.assertEqual(cp["unvisited_boards"], ["automattic"])
        self.assertEqual(cp["trace"], f"traces/trace_TESTRUN.jsonl")

    def test_current_constants_are_the_gate_values(self):
        self.assertEqual((cfg.MAX_SECONDS, cfg.MAX_REQUESTS, cfg.MAX_BOARDS), (60.0, 12, 5))


# ============================================================ repeat rule
class RepeatRule(SandboxTest):
    boards = [gh("cloudflare"), gh("cloudflare"), lever("automattic")]

    def test_key_has_no_attempt_number(self):
        board = Board(0, "greenhouse", "cloudflare", CF, False, None)
        self.assertEqual(board.key, ("greenhouse", "cloudflare", "GET", CF))

    def test_repeat_is_a_cache_hit_without_a_request(self):
        report = self.sb.run({CF: [ok("greenhouse_three_jobs.json")], AU: [ok("lever_two_jobs.json")]})
        self.assertEqual(report["status"], "SUCCESS")
        self.assertEqual(report["budget"]["requests_used"], 2)
        self.assertEqual([u for u, _ in self.sb.transport.calls], [CF, AU])
        hits = [line for line in self.sb.trace_lines() if line["event"] == "IDEMPOTENT_CACHE_HIT"]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["job_count"], 3)
        self.assertTrue(report["boards"][1]["cache_hit"])

    def test_retry_is_exempt_and_counts_against_max_requests(self):
        report = self.sb.run({CF: [status(503), ok("greenhouse_three_jobs.json")], AU: [ok("lever_two_jobs.json")]})
        self.assertEqual(report["status"], "SUCCESS")
        self.assertEqual([u for u, _ in self.sb.transport.calls], [CF, CF, AU])  # retry went out; repeat did not
        self.assertEqual(report["budget"]["requests_used"], 3)
        self.assertEqual([line["attempt"] for line in self.attempts() if line["board"] == "cloudflare"], [1, 2])

    def test_retry_blocked_when_it_would_pass_max_requests(self):
        report = self.sb.run({CF: [status(503)]}, budgets=dict(cfg.BUDGETS, max_requests=1))
        self.assertEqual(report["budget"]["tripped"], "max_requests")
        self.assertEqual(len(self.sb.transport.calls), 1)

    def test_repeat_of_a_failed_board_reuses_the_failure(self):
        report = self.sb.run({CF: [status(404)], AU: [ok("lever_two_jobs.json")]})
        self.assertEqual([b["error_code"] for b in report["boards"]], ["BOARD_NOT_FOUND", "BOARD_NOT_FOUND", None])
        self.assertIsNone(report["boards"][1]["job_count"])
        self.assertEqual(len(self.sb.transport.calls), 2)

    def test_cache_lasts_one_run_only(self):
        script = {CF: [ok("greenhouse_three_jobs.json")], AU: [ok("lever_two_jobs.json")]}
        self.sb.run(script, run_id="RUN_A")
        self.sb.run(script, run_id="RUN_B")
        self.assertEqual([u for u, _ in self.sb.transport.calls], [CF, AU])  # the second run fetched again


# ============================================================ error policy rows
class ErrorPolicy(SandboxTest):
    boards = [gh("cloudflare"), lever("automattic")]

    def run_cf(self, steps):
        report = self.sb.run({CF: steps, AU: [ok("lever_two_jobs.json")]})
        self.assertEqual(by_board(report)["automattic"]["outcome"], "verified")  # isolation
        return report, by_board(report)["cloudflare"]

    def test_timeout_retries_once_after_1_5s_then_exhausted(self):
        report, cf = self.run_cf([timeout(), timeout()])
        self.assertEqual(cf["error_code"], "TIMEOUT_EXHAUSTED")
        self.assertIsNone(cf["job_count"])
        self.assertEqual(cf["attempts"], 2)
        self.assertEqual(self.sb.sleep.calls, [1.5])
        self.assertEqual(report["status"], "PARTIAL_SUCCESS")

    def test_timeout_then_success_is_verified(self):
        report, cf = self.run_cf([timeout(), ok("greenhouse_three_jobs.json")])
        self.assertEqual((cf["outcome"], cf["job_count"]), ("verified", 3))
        self.assertEqual(report["status"], "SUCCESS")

    def test_5xx_retries_once_after_2s_then_records_status(self):
        report, cf = self.run_cf([status(503, fixture("html_503.html")), status(502)])
        self.assertEqual((cf["error_code"], cf["http_status"]), ("UPSTREAM_5XX_ERROR", 502))
        self.assertEqual(self.sb.sleep.calls, [2.0])
        self.assertEqual(len(report["raw_files"]), 3)  # both 5xx bodies saved, plus automattic

    def test_429_retries_once_then_exhausted(self):
        _, cf = self.run_cf([status(429), status(429)])
        self.assertEqual((cf["error_code"], cf["http_status"]), ("RATE_LIMITED_EXHAUSTED", 429))

    def test_404_is_not_retried(self):
        _, cf = self.run_cf([status(404)])
        self.assertEqual((cf["error_code"], cf["http_status"], cf["attempts"]), ("BOARD_NOT_FOUND", 404, 1))
        self.assertEqual(self.sb.sleep.calls, [])

    def test_verified_empty_is_zero_and_success(self):
        report, cf = self.run_cf([ok("greenhouse_empty_verified.json")])
        self.assertEqual((cf["outcome"], cf["job_count"]), ("verified", 0))
        self.assertEqual(report["status"], "SUCCESS")

    def test_suspicious_empty_is_failed_with_null_count(self):
        report, cf = self.run_cf([ok("greenhouse_empty_meta_says_50.json")])
        self.assertEqual((cf["error_code"], cf["job_count"], cf["attempts"]), ("SUSPICIOUS_PAYLOAD", None, 1))
        self.assertEqual(report["status"], "PARTIAL_SUCCESS")

    def test_malformed_body_saved_to_traces_malformed(self):
        report, cf = self.run_cf([ok("html_challenge.html")])
        self.assertEqual((cf["error_code"], cf["attempts"]), ("PARSE_SCHEMA_MISMATCH", 1))
        (saved,) = report["malformed_files"]
        self.assertTrue(saved["path"].startswith("traces/malformed/"))
        self.assertEqual((self.sb.root / saved["path"]).read_bytes(), fixture("html_challenge.html"))

    def test_cut_off_body_is_truncated_and_saved_as_malformed(self):
        report, cf = self.run_cf([ok("greenhouse_truncated_syntax.json")])
        self.assertEqual(cf["error_code"], "TRUNCATED_RESPONSE")
        self.assertEqual(len(report["malformed_files"]), 1)

    def test_count_truncation_records_meta_total_and_jobs_in_body(self):
        report, cf = self.run_cf([ok("greenhouse_truncated_count.json")])
        self.assertEqual(cf["error_code"], "TRUNCATED_RESPONSE")
        self.assertIsNone(cf["job_count"])
        line = [a for a in self.attempts() if a["board"] == "cloudflare"][0]
        self.assertEqual(line["observations"]["meta_total"], 5)
        self.assertEqual(line["observations"]["jobs_in_body"], 2)
        self.assertIsNone(line["job_count"])

    def test_wrong_root_key_is_not_zero_jobs(self):
        _, cf = self.run_cf([ok("greenhouse_wrong_root_key.json")])
        self.assertEqual(cf["error_code"], "PARSE_SCHEMA_MISMATCH")
        self.assertIsNone(cf["job_count"])

    def test_connection_error_not_retried(self):
        _, cf = self.run_cf([error("CONNECTION_ERROR")])
        self.assertEqual((cf["error_code"], cf["attempts"], cf["http_status"]), ("NETWORK_ERROR", 1, None))

    def test_redirect_refused(self):
        _, cf = self.run_cf([status(301)])
        self.assertEqual(cf["error_code"], "REDIRECT_REFUSED")

    def test_other_http_status(self):
        _, cf = self.run_cf([status(403)])
        self.assertEqual((cf["error_code"], cf["http_status"]), ("HTTP_ERROR", 403))

    def test_unexpected_transport_exception_is_recorded_not_raised(self):
        report, cf = self.run_cf([boom(RuntimeError("socket library bug"))])
        self.assertEqual(cf["error_code"], "TRANSPORT_EXCEPTION")
        self.assertIn("RuntimeError", self.attempts()[0]["detail"])
        self.assertEqual(report["exit_code"], 2)

    def test_no_failure_ever_reports_a_job_count(self):
        for steps in ([status(404)], [timeout(), timeout()], [ok("html_challenge.html")],
                      [ok("greenhouse_empty_meta_says_50.json")]):
            with self.subTest(steps=steps[0].get("status", steps[0].get("error"))):
                self.sb.cleanup()
                self.sb = Sandbox(self.boards)
                _, cf = self.run_cf(steps)
                self.assertIsNone(cf["job_count"])
                self.assertIsNotNone(cf["error_code"])


# ============================================================ state
class State(SandboxTest):
    boards = [gh("cloudflare"), lever("automattic")]

    def test_verified_board_replaces_ids_and_reports_diff(self):
        self.sb.run({CF: [ok("greenhouse_three_jobs.json")], AU: [ok("lever_two_jobs.json")]}, run_id="R1")
        self.assertIsNone(self.sb.state("cloudflare")["ledger"][0]["diff"])  # baseline
        report = self.sb.run({CF: [ok("greenhouse_three_jobs_next.json")], AU: [ok("lever_two_jobs.json")]},
                             run_id="R2")
        state = self.sb.state("cloudflare")
        self.assertEqual(state["active_job_ids"], [102, 103, 104])  # replaced: 101 is gone, not merged
        self.assertEqual(by_board(report)["cloudflare"]["diff"], {"added": [104], "removed": [101], "unchanged": 2})
        self.assertEqual(len(state["ledger"]), 2)

    def test_failed_board_keeps_ids_and_appends_error(self):
        self.sb.run({CF: [ok("greenhouse_three_jobs.json")], AU: [ok("lever_two_jobs.json")]}, run_id="R1")
        self.sb.run({CF: [status(404)], AU: [ok("lever_two_jobs.json")]}, run_id="R2")
        state = self.sb.state("cloudflare")
        self.assertEqual(state["active_job_ids"], [101, 102, 103])
        self.assertEqual(state["ledger"][-1]["error_code"], "BOARD_NOT_FOUND")
        self.assertIsNone(state["ledger"][-1]["job_count"])

    def test_first_run_failure_has_null_ids_not_empty_list(self):
        self.sb.run({CF: [status(404)], AU: [ok("lever_two_jobs.json")]})
        self.assertIsNone(self.sb.state("cloudflare")["active_job_ids"])

    def test_unvisited_board_state_is_untouched(self):
        path = self.sb.state_file("automattic")
        path.parent.mkdir(parents=True)
        before = json.dumps({"board_token": "automattic", "provider": "lever",
                             "active_job_ids": ["old"], "ledger": []})
        path.write_text(before)
        self.sb.run({CF: [ok("greenhouse_three_jobs.json")]}, budgets=dict(cfg.BUDGETS, max_requests=1))
        self.assertEqual(path.read_text(), before)

    def test_state_for_another_provider_is_fatal(self):
        path = self.sb.state_file("cloudflare")
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"board_token": "cloudflare", "provider": "lever",
                                    "active_job_ids": [], "ledger": []}))
        self.assertEqual(self.sb.run({})["exit_code"], 1)


# ============================================================ files and paths
class Files(SandboxTest):
    def test_trace_has_one_line_per_attempt_with_required_fields(self):
        self.sb.run(dict(REAL_OK, **{CF: [status(503), ok("greenhouse_three_jobs.json")]}))
        attempts = self.attempts()
        self.assertEqual(len(attempts), 4)
        for line in attempts:
            for field in ("board", "provider", "url", "attempt", "http_status", "error_kind", "job_count",
                          "observations", "decision", "budget_remaining"):
                self.assertIn(field, line)
        self.assertEqual(attempts[0]["decision"], "RETRY")
        self.assertEqual(attempts[0]["budget_remaining"]["requests"], 11)

    def test_raw_bodies_saved_under_output_raw_run_id(self):
        report = self.sb.run(REAL_OK)
        for f in report["raw_files"]:
            self.assertTrue(f["path"].startswith("output/raw/TESTRUN/"))
        self.assertEqual((self.sb.root / report["raw_files"][0]["path"]).read_bytes(),
                         fixture("greenhouse_three_jobs.json"))

    def test_existing_trace_is_never_overwritten(self):
        trace = self.sb.root / "traces" / "trace_TESTRUN.jsonl"
        trace.parent.mkdir()
        trace.write_text("earlier run\n")
        report = self.sb.run(REAL_OK)
        self.assertEqual(report["exit_code"], 1)
        self.assertEqual(trace.read_text(), "earlier run\n")
        self.assertEqual(self.sb.transport.calls, [])

    def test_existing_raw_file_is_never_overwritten(self):
        raw = self.sb.root / "output/raw/TESTRUN/greenhouse_cloudflare_attempt1.body"
        raw.parent.mkdir(parents=True)
        raw.write_bytes(b"earlier")
        report = self.sb.run(REAL_OK)
        self.assertEqual((report["exit_code"], report["error"]["subsystem"]), (1, "filesystem"))
        self.assertEqual(raw.read_bytes(), b"earlier")

    def test_paths_resolve_against_root_not_cwd(self):
        elsewhere = tempfile.mkdtemp()
        old = os.getcwd()
        os.chdir(elsewhere)
        try:
            report = self.sb.run(REAL_OK)
        finally:
            os.chdir(old)
        self.assertEqual(report["status"], "SUCCESS")
        self.assertEqual(os.listdir(elsewhere), [])
        self.assertTrue((self.sb.root / "traces/trace_TESTRUN.jsonl").is_file())
        os.rmdir(elsewhere)


class IORouting(SandboxTest):
    """Every network call and file read/write goes through the SecurityPolicy validators."""

    def test_all_io_passes_through_the_policy(self):
        events = []

        class Recording(SecurityPolicy):
            def validate_network_request(self, method, u):
                events.append(("net", u))

            def validate_file_read(self, path):
                events.append(("read", Path(path).resolve()))

            def validate_file_write(self, path):
                events.append(("write", Path(path).resolve()))

        self.sb.run(dict(REAL_OK, **{CF: [ok("html_challenge.html")]}), policy=Recording())
        nets = [u for kind, u in events if kind == "net"]
        self.assertEqual(nets, [u for u, _ in self.sb.transport.calls])
        written = {p for kind, p in events if kind == "write"}
        for top in ("output", "traces"):
            for path in (self.sb.root / top).rglob("*"):
                self.assertIn(path.resolve(), written, f"{path} was written without validate_file_write")
        self.assertIn(("read", (self.sb.root / self.sb.config).resolve()), events)


if __name__ == "__main__":
    unittest.main()
