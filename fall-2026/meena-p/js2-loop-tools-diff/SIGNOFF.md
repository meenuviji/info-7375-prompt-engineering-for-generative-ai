# Sign-off — Job-Search Agent 2

## Checked

- **Network permissions:** The agent only allows HTTPS GET requests to the approved Greenhouse and Lever hosts and rejects requests to other hosts, lookalike domains, and non-HTTPS URLs — checked through boundary tests 1–5 and 14.
- **File permissions:** The agent allows writes only to approved locations and blocks path traversal, prefix tricks, symlink escapes, and unauthorized config changes — checked through boundary tests 6–13 and 16.
- **Disallowed boards:** A board pointing to an unapproved host is rejected without sending a request, while the agent can continue processing other boards — checked through boundary test 17.
- **Credential protection:** I wrote `test_no_credentials_sent_from_netrc` before the credential fix. The test initially failed because Requests was automatically attaching credentials from a `.netrc` file. After the fix, the same test passed.
- **Regression tests:** I ran the complete test suite after the credential fix and got 89 passed and 4 subtests passed.
- **Independent checking:** I tested the independent checker using a deliberately truncated Cloudflare response to see whether an incorrect result could be detected. The agent also identifies truncated responses as `TRUNCATED_RESPONSE`.

## How

- **By hand:** I reviewed the permission rules in `GATE.md`, wrote my predictions in `BOUNDARY_TESTS.md` before implementation, and compared the expected behavior with the test results. I also reviewed the changes made to `src/fetch.py` for the credential issue.
- **By a test I wrote before reading Claude's code:** I wrote `test_no_credentials_sent_from_netrc` to check whether the transport could accidentally send credentials stored in `.netrc`. I used a fake credentials file and intercepted the request instead of making a real network call. The test failed before the patch because an Authorization header was present. After the patch, it passed.
- **By recomputation:** I reran the credential test and the complete test suite after the fix. I also used the independent checker to compare results rather than relying only on the agent's reported success. The full suite returned 89 passed and 4 subtests passed.
- **With Claude's help:** Claude helped me plan the implementation, understand how the permission checks should work, and identify the areas that needed testing. Claude Code implemented the permission policy and the credential fix. Claude also helped with the structure and wording of some documentation. I reviewed the results, made the decisions about the permission boundaries, and accepted the changes based on the evidence from the tests.

## Not checked

1. I did not test every possible URL format, including URLs with embedded usernames and passwords. The current provider templates do not generate these URLs, but the policy does not explicitly reject all of them.
2. I did not independently test every redirect scenario at the policy level. Redirects are disabled in the HTTP transport using `allow_redirects=False`, but I have not verified every possible redirect behavior.
3. I did not test the agent against every real-world API response or every possible change in the Greenhouse and Lever APIs. Most of my verification used controlled and offline test cases.

## Not claiming

- I am not claiming that the agent is completely secure or that every possible edge case has been tested.
- I am not claiming that passing the test suite guarantees correct behavior for every live API response.
- I am not claiming that I independently wrote all the implementation code. Claude Code helped with the implementation, while I was responsible for reviewing the work, checking the results, and making the final decisions.
- I am not claiming that the independent checker covers every possible incorrect output.

## Signed or withheld

**Meena Periasamy, 2026-11-10 — Signed.**

I am signing off on the behavior I tested and reviewed. The permission boundary tests, the credential-leak test, and the full test suite give me enough evidence that the implemented controls work for the cases I checked.

I understand that there are still limitations and cases I have not tested. I have listed those rather than claiming that the system is fully verified.

## Driver's seat

| Part | What Claude should do | What I should do | Why that part stays mine | Evidence |
|---|---|---|---|---|
| The loop | Help implement the agent, write the permission checks, handle errors, and suggest improvements based on the requirements. | Define the requirements, decide what behavior is allowed, make predictions before implementation, and verify that the agent follows those decisions. | I need to understand what the agent is doing and decide what it is permitted to do. Claude can help implement the logic, but the requirements and final decisions should come from me. | `GATE.md`, `BOUNDARY_TESTS.md`, permission boundary tests, and test results in `notes/`. |
| The review | Help explain the implementation, suggest testing approaches, fix identified issues, and organize the review documentation. | Write and run an independent test, inspect the failure, review the proposed fix, rerun the tests, and decide whether the evidence is sufficient to sign off. | The review should not depend only on Claude saying its own code works. I need to check the evidence myself and be able to explain what was tested, what failed, and why I accepted the fix. | `tests/test_review_no_credentials.py`, `review/01_test_fails_before_patch.txt`, `review/03_test_passes_after_patch.txt`, `review/04_full_suite_after_patch.txt`, and `SIGNOFF.md`. |
