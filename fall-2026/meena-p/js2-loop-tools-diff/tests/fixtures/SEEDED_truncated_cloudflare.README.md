# SEEDED_truncated_cloudflare.json

**This is a seeded fixture, deliberately damaged.** It is not a real Greenhouse response.

- **Source:** `output/real_run/20261110T203921572430Z/raw/greenhouse_cloudflare_attempt1.body`.
  That is the real Cloudflare response from the live run of 2026-11-10 20:39:21 UTC
  (`config/boards.json`), fetched from
  `https://boards-api.greenhouse.io/v1/boards/cloudflare/jobs?content=true`.
  - SHA-256 of the source: `9a43d1647f15b57c4ad8a522f04fe9e504c369c4e2f0b0bae62ba3bdea5b585d`.
    The run-1 copy (`20261110T203826744076Z`) is byte-identical.
- **What was changed:** the **last 18 entries** of `"jobs"` were removed: 468 jobs in the source, 450 here.
  `meta.total` was left at **468**. Nothing else was edited.
- **Removed job ids, in their original order:**
  7804941, 8168940, 8233344, 8329671, 8045309, 8335468, 7857793, 8279346, 8345223,
  8172404, 8172411, 8190563, 8212088, 8245503, 8204353, 8158104, 8256449, 8332823.
- **Serialization:** the file was loaded and re-written with Python's `json.dump(...,
  ensure_ascii=False, separators=(",", ":"))`. The bytes therefore differ from the source:
  6,899,353 bytes here against 8,303,393 in the source. That comes from the 18 removed
  entries and from non-ASCII text now written directly instead of as `\u` escapes. All
  other values are the same.
  - Re-serializing the unmodified source gives 7,143,528 bytes (the source contains 231,973
    `\u` escapes). The 18 removed entries account for a further 244,176 bytes.
- **Purpose:** to reproduce GATE.md 4.2's count-truncation case (`meta.total > len(jobs)`)
  for the finished-but-wrong demonstration in `output/demo/FINISHED_WRONG.md`.
