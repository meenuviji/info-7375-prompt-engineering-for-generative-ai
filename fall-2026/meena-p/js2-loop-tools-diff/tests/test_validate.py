"""Structural validation (GATE.md section 4). No network, no files beyond fixtures."""

import unittest

from src.validate import looks_truncated, parse_board
from tests.helpers import fixture


class GreenhouseValidation(unittest.TestCase):
    def test_three_jobs_verified(self):
        v = parse_board("greenhouse", fixture("greenhouse_three_jobs.json"))
        self.assertTrue(v.ok)
        self.assertEqual(v.job_count, 3)
        self.assertEqual(v.job_ids, (101, 102, 103))

    def test_small_minified_body_with_a_job_is_not_empty(self):
        # Wrong version: a byte-size check would call this 38-byte body empty.
        body = fixture("greenhouse_minified_one_job.json")
        self.assertLess(len(body), 300)
        v = parse_board("greenhouse", body)
        self.assertTrue(v.ok)
        self.assertEqual(v.job_count, 1)

    def test_large_verified_empty_is_zero(self):
        # Wrong version: a byte-size check would call this padded 470-byte body suspicious.
        body = fixture("greenhouse_empty_verified.json")
        self.assertGreater(len(body), 300)
        v = parse_board("greenhouse", body)
        self.assertTrue(v.ok)
        self.assertEqual(v.job_count, 0)

    def test_empty_list_with_meta_total_50_is_suspicious(self):
        v = parse_board("greenhouse", fixture("greenhouse_empty_meta_says_50.json"))
        self.assertEqual(v.error_code, "SUSPICIOUS_PAYLOAD")
        self.assertIsNone(v.job_count)

    def test_empty_list_without_meta_is_not_a_verified_zero(self):
        v = parse_board("greenhouse", b'{"jobs": []}')
        self.assertFalse(v.ok)
        self.assertIsNone(v.job_count)

    def test_wrong_root_key_is_a_mismatch_not_zero(self):
        # Wrong version: data.get("jobs", []) would report 0 jobs for 50 postings.
        v = parse_board("greenhouse", fixture("greenhouse_wrong_root_key.json"))
        self.assertEqual(v.error_code, "PARSE_SCHEMA_MISMATCH")
        self.assertIsNone(v.job_count)

    def test_meta_total_greater_than_jobs_is_truncated(self):
        v = parse_board("greenhouse", fixture("greenhouse_truncated_count.json"))
        self.assertEqual(v.error_code, "TRUNCATED_RESPONSE")
        self.assertEqual(v.observations["meta_total"], 5)
        self.assertEqual(v.observations["jobs_in_body"], 2)
        self.assertIsNone(v.job_count)

    def test_meta_total_less_than_jobs_is_a_mismatch(self):
        v = parse_board("greenhouse", b'{"jobs": [{"id": 1}, {"id": 2}], "meta": {"total": 1}}')
        self.assertEqual(v.error_code, "PARSE_SCHEMA_MISMATCH")

    def test_cut_off_json_is_truncated(self):
        v = parse_board("greenhouse", fixture("greenhouse_truncated_syntax.json"))
        self.assertEqual(v.error_code, "TRUNCATED_RESPONSE")
        self.assertEqual(v.observations["truncation"], "syntax")

    def test_html_is_a_mismatch(self):
        v = parse_board("greenhouse", fixture("html_challenge.html"))
        self.assertEqual(v.error_code, "PARSE_SCHEMA_MISMATCH")

    def test_job_without_id_is_a_mismatch(self):
        v = parse_board("greenhouse", fixture("greenhouse_job_missing_id.json"))
        self.assertEqual(v.error_code, "PARSE_SCHEMA_MISMATCH")

    def test_boolean_meta_total_and_ids_are_rejected(self):
        self.assertFalse(parse_board("greenhouse", b'{"jobs": [], "meta": {"total": false}}').ok)
        self.assertFalse(parse_board("greenhouse", b'{"jobs": [{"id": true}], "meta": {"total": 1}}').ok)

    def test_non_utf8_and_empty_bodies_are_mismatches(self):
        self.assertEqual(parse_board("greenhouse", b"\xff\xfe\x00").error_code, "PARSE_SCHEMA_MISMATCH")
        self.assertEqual(parse_board("greenhouse", b"").error_code, "PARSE_SCHEMA_MISMATCH")


class LeverValidation(unittest.TestCase):
    def test_two_jobs_verified(self):
        v = parse_board("lever", fixture("lever_two_jobs.json"))
        self.assertTrue(v.ok)
        self.assertEqual(v.job_count, 2)

    def test_empty_list_is_suspicious_because_lever_has_no_count(self):
        v = parse_board("lever", fixture("lever_empty.json"))
        self.assertEqual(v.error_code, "SUSPICIOUS_PAYLOAD")
        self.assertIsNone(v.job_count)

    def test_object_root_is_a_mismatch(self):
        v = parse_board("lever", fixture("greenhouse_three_jobs.json"))
        self.assertEqual(v.error_code, "PARSE_SCHEMA_MISMATCH")


class TruncationScanner(unittest.TestCase):
    def test_cases(self):
        self.assertTrue(looks_truncated('{"a": [1, 2'))
        self.assertTrue(looks_truncated('{"a": "unterminated'))
        self.assertTrue(looks_truncated('[{"a": "brace } inside string"'))
        self.assertFalse(looks_truncated('{"a": 1}}'))   # extra closer: broken, not cut off
        self.assertFalse(looks_truncated("<html>"))
        self.assertFalse(looks_truncated(""))


if __name__ == "__main__":
    unittest.main()
