## Permission boundary tests — My predictions

These are my predictions based on my understanding of the permission rules in GATE.md sections 9.5 and 9.9, before implementing the policy or running the tests.

| #  | Case                                   | Input | Predicted                                                                               | Actual  | Match?  |
| -- | -------------------------------------- | ----- | --------------------------------------------------------------------------------------- | ------- | ------- |
| 1  | Allowed host                           | GET https://boards-api.greenhouse.io/v1/boards/cloudflare/jobs | ALLOW — HTTPS GET to an approved Greenhouse host                                        | ALLOW — no denial (test_boundary_01 passed) | Yes |
| 2  | Second allowed host                    | GET https://api.lever.co/v0/postings/palantir?mode=json | ALLOW — HTTPS GET to an approved Lever host                                             | ALLOW — no denial (test_boundary_02 passed) | Yes |
| 3  | Host off allow-list                    | GET https://example.com/jobs | DENY — example.com is not an approved host                                              | DENY — `net.host-not-allowed` (test_boundary_03 passed) | Yes |
| 4  | Lookalike host                         | GET https://boards-api.greenhouse.io.evil.com/jobs | DENY — the hostname is not an exact match                                               | DENY — `net.host-not-allowed` (test_boundary_04 passed) | Yes |
| 5  | Non-HTTPS                              | GET http://boards-api.greenhouse.io/v1/boards/cloudflare/jobs | DENY — only HTTPS requests are permitted                                                | DENY — `net.scheme-not-https` (test_boundary_05 passed) | Yes |
| 6  | Write inside an allowed folder         | write output/raw/test.json | ALLOW — the file is inside output/                                                      | ALLOW — no denial (test_boundary_06 passed) | Yes |
| 7  | Path traversal                         | write output/../GATE.md | DENY — the resolved path escapes output/                                                | DENY — `file.write-outside-allowed-folders` (test_boundary_07 passed) | Yes |
| 8  | Prefix trick                           | write output-evil/x.json | DENY — output-evil/ is not the same as output/                                          | DENY — `file.write-outside-allowed-folders` (test_boundary_08 passed) | Yes |
| 9  | Symlink escape                         | output/link points to /tmp; write output/link/x.json | DENY — the symlink resolves outside the allowed folder                                  | DENY — `file.write-outside-allowed-folders` (test_boundary_09 passed) | Yes |
| 10 | Read vs write, same file               | read config/boards.json, then write config/boards.json (no approval flag) | ALLOW read, DENY write — reading config is permitted, but writing requires approval     | ALLOW read, DENY write — `file.config-write-needs-approval` (test_boundary_10 passed) | Yes |
| 11 | Approval-required write, no approval   | write config/boards.json without --approve-config-write | DENY — the required approval flag is missing                                            | DENY — `file.config-write-needs-approval` (test_boundary_11 passed) | Yes |
| 12 | Approval-required write, with approval | write config/boards.json with --approve-config-write | ALLOW — the approval flag permits writing to config/                                    | ALLOW — no denial; `--approve-config-write` sets it (test_boundary_12 passed) | Yes |
| 13 | Outside write even with approval       | write /tmp/x.json with --approve-config-write | DENY — approval does not override path restrictions                                     | DENY — `file.write-outside-allowed-folders` (test_boundary_13 passed) | Yes |
| 14 | Non-GET request                        | POST https://boards-api.greenhouse.io/v1/boards/cloudflare/jobs | DENY — POST requests are not permitted                                                  | DENY — `net.method-not-get` (test_boundary_14 passed) | Yes |
| 15 | Credentials in environment             | a ~/.netrc entry for boards-api.greenhouse.io exists; fetch Cloudflare | ALLOW fetch without credentials — the request should not use credentials from ~/.netrc | ALLOW fetch, no Authorization header — netrc entry supplied via $NETRC; header leaked before the src/fetch.py patch (review/01), absent after (tests/test_review_no_credentials.py passed, review/03, 893704f) | Yes |
| 16 | Config path outside config/            | run with --config /tmp/boards.json | DENY — the config file is outside the permitted directory                               | DENY — `file.config-path-outside-config`, exit 1 (test_boundary_16 passed) | Yes |
| 17 | Board on a disallowed host in config   | config lists a board whose URL is on example.com | DENY — a URL in config must still satisfy the host allow-list                           | DENY — `net.host-not-allowed`: POLICY_DENIED, no request sent, other boards run, PARTIAL_SUCCESS exit 2 (test_boundary_17 passed) | Yes |

### My reasoning

My understanding is that the permission policy should follow a default-deny approach, where an operation is allowed only when it satisfies the defined rules.

For network requests, I expect the system to check the request method, HTTPS scheme, and exact hostname rather than trusting URLs that only look similar to approved ones.

For file operations, I expect the system to validate the resolved path, not just the beginning of the path string. This should prevent directory traversal, prefix tricks, and symlink escapes.

I also expect read and write permissions to be handled separately. The approval flag should authorize only specific protected writes, not bypass all permission restrictions.

For credentials, my prediction is that the fetch should work without automatically using credentials available in the environment.

My overall expectation: Cases 1, 2, 6, and 12 should be allowed; case 10 should allow only the read; case 15 should allow a credential-free fetch; and the remaining cases should be denied.

I would leave the Actual and Match? columns pending until the implementation is complete and the tests have been executed. I checked these predictions against GATE.md 9.5 before committing them.

### Row 17 outcome

Row 17: that board fails with POLICY_DENIED, no request is sent, and the run continues to the other boards, ending PARTIAL_SUCCESS (exit 2). My reason: one bad line in the config should not hide the other boards (GATE.md 9.10).

Note on row 17 (added after implementation): the test uses a test-only provider pointing at example.com, because a real config builds every URL from the Greenhouse or Lever template and cannot reach a disallowed host. See GATE.md 9.11.
