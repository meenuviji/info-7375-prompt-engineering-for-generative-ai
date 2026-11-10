# FRICTIONAL — Job-Search Agent 2

Meena Periasamy — 2026-11-10

This is my record of the places where the project did not go exactly as planned. I have included mistakes in my own workflow, problems Claude or Claude Code identified, decisions I made, and things I still have not verified. The commit hashes are here so I can trace the work instead of relying only on what I remember.

## 1. Cutting the scope from JS1

**Reference:** JS1 to JS2 carryover; see the initial JS2 commits.

I decided to carry over only `fetch.py` and `state.py` from JS1 instead of copying the entire previous project. I wanted JS2 to have a smaller starting point and to make the new loop and its rules explicit.

This meant more work rebuilding the surrounding pieces, but it also made it easier to separate what was reused from what was newly implemented. I accepted the smaller scope rather than bringing in code I could not clearly justify.

## 2. Claude Code refused the first gate

**Reference:** Initial `GATE.md`; see the gate revision history.

When I first gave Claude Code the gate, it refused to build and identified 11 contradictions. I had expected implementation to start, but the requirements were not consistent enough.

I went back to the gate instead of asking Claude Code to work around the contradictions. I learned that writing a requirement is not the same as making it implementable. If two rules conflict, the implementation cannot reliably follow both.

## 3. The commit message did not match the gate

**Commit:** `667e5e7`

This commit said the contradictions were resolved, but the gate itself was still unedited. I had relied on the commit message without checking that the intended changes were actually present.

I learned to inspect the committed content, not just the message describing it. A commit message is a claim about the work, not proof that the work was done.

## 4. I was editing the wrong copy of GATE.md

**Reference:** `667e5e7` and the subsequent gate corrections.

There were two copies of `GATE.md`, and I had been editing the untracked JS1 copy instead of the JS2 file I intended to change.

This explained why the committed gate did not contain my revisions. I corrected the file-location mistake and learned to check the repository path and `git status` before committing. I also learned that a file can look correct in my editor while the repository still contains an older version.

## 5. The AGENTS.md import prompt

**Reference:** Initial Claude Code setup; `AGENTS.md`.

Claude Code presented an `AGENTS.md` import decision. I treated this as a question about which instructions should control the new project, rather than something to accept automatically.

My priority was keeping the JS2 gate as the source of the project's requirements. I did not want imported instructions from the earlier project to silently change the new scope.

The exact prompt selection should be checked against the original session record before I claim which option I selected.

## 6. The loop was built in auto mode

**Reference:** Initial loop implementation commits.

Claude Code ran the loop build in auto mode for 9 minutes and 44 seconds. I did not review each edit while it was being made. I reviewed the result afterward.

I accepted using automation for the implementation, but I still needed to inspect what had changed and test whether it followed my requirements. This showed me the difference between allowing Claude to write code and accepting responsibility for the final behavior.

## 7. Automattic returned 404

**Reference:** Provider verification during the loop build.

Claude Code reported that the Automattic board returned HTTP 404. I did not treat that as proof that all the provider integrations were broken.

I independently checked Palantir and Datadog to see whether the issue was specific to one board. The lesson was to separate a problem with a particular endpoint from a problem with the fetching logic.

I also learned not to assume that a company board will remain available just because it was valid earlier.

## 8. pytest was missing

**Reference:** Initial test setup and the run reporting 71 passing tests.

The virtual environment did not have `pytest`, and it was also missing from `requirements.txt`. That meant the project was not fully reproducible from the dependency file.

I addressed the test setup and ran the tests myself. My run confirmed 71 passing tests at that stage.

I learned that a working codebase is not enough if a fresh environment cannot run its tests. The dependency list is part of the deliverable.

## 9. A commit referred to work that did not exist

**Commit:** `d9590a3`

This commit referred to a report and a review that had not been created yet. The message made the project sound further along than the files supported.

I learned to distinguish planned work from completed work and to check that referenced artifacts actually exist before describing them as finished.

## 10. The gate was accidentally truncated

**Commits:** `0218bbd` and `3f48500`

Commit `0218bbd` truncated `GATE.md` at section 5.1. That was a serious documentation problem because the later requirements were missing.

I restored the missing material in `3f48500`.

This taught me to inspect the entire document after major edits, especially when a tool is rewriting a file. A successful command does not guarantee that the resulting document is complete.

## 11. Claude's section 9 draft contradicted itself

**Reference:** `GATE.md` section 9.9 and its revision history.

Claude drafted section 9, but items 1, 6, and 10 were inconsistent with each other. Claude Code identified the contradiction.

I revised the requirements in section 9.9 rather than letting the implementation choose between conflicting instructions.

I accepted the contradiction report, but changed the specification myself. I learned that Claude can help detect inconsistencies, but I still need to decide which behavior I actually want.

## 12. Section 9.10 was missing from the claimed commit

**Commits:** `fd0e047` and `9a87c85`

Commit `fd0e047` claimed section 9.10 had been added, but it was not present.

I added it in `9a87c85`.

This was another reminder to check the actual files after committing. I cannot use the commit message alone as evidence that a requirement has been implemented or documented.

## 13. The boundary tests landed in a different commit

**Commits:** `bf53866` and `e2ff0aa`

The message for `bf53866` claimed the boundary tests were included, but they actually landed in `e2ff0aa`.

I learned to use `git show --stat` to confirm which files a commit changed. This matters for traceability because I need to point to the commit containing the evidence, not just the one whose message mentions it.

## 14. Claude Code changed two existing tests

**Reference:** Boundary-test implementation and review around `bf53866` and `e2ff0aa`.

Claude Code changed two tests that already existed. I reviewed both diffs rather than accepting the changes based only on the passing test suite.

One change corrected the test and made its condition stricter. The other tested only the root case. From my review, neither change weakened the original test requirement.

I accepted the changes after checking their purpose. I learned that a test modification needs review just as much as a production-code modification, because changing the test can sometimes hide a bug rather than fix it.

## 15. My first review defect was not actually a defect

**Reference:** `GATE.md` section 5.3; review planning.

I initially planned to review behavior that looked incorrect. When I checked it against section 5.3, I found that it was actually the behavior the gate specified.

I rejected that as a valid defect and switched to investigating whether credentials from `.netrc` could leak into an outgoing request.

This was important because I did not want to call something a bug just because it differed from my first expectation. The specification had to be my reference point.

## 16. The unexpected review folder was mine

**Commit:** `04216ee`

I initially treated the `review/` folder as unexpected. After checking the earlier work, I found that it came from my own previous run.

I moved the earlier evidence into `notes/unexpected_review_folder/`.

I learned to check my own command history and repository state before assuming a file or folder was created by Claude Code.

## 17. I used the wrong Python environment

**Commit:** `c799546`

I first tried to run the review test using `python`, which was not available as a command on my Mac. I then used the system `python3`, which was Python 3.9, and installed `pytest` and `requests` there.

That was not the environment I intended to use for this project.

I corrected the workflow by running the test through `.venv/bin/python`, which used Python 3.12. The credential leak was reproduced with both Requests versions.

The test showed that the request contained an `Authorization` header with the fake credentials from `.netrc`.

I learned to use the project's virtual environment consistently and to verify which interpreter is running my tests.

## 18. My decision on the credentials patch

**Commits:** `c799546`, `893704f`, and `45e85dc`

**Decision: Accepted the credential fix for the behavior I tested.**

My test, `test_no_credentials_sent_from_netrc`, failed before the patch because Requests automatically read the fake credentials from `.netrc` and added an Authorization header.

The patch introduced an explicit no-op authentication function, `_no_auth`, and passed it to `requests.get()`. This prevented Requests from adding the `.netrc` credentials in the tested case.

I reran my review test after the patch and it passed. I also ran the complete suite, which returned 89 passed and 4 subtests passed.

I accepted the patch because it directly addressed the failure I had reproduced and did not break the existing tests. I did not treat that as proof that every possible credential source or authentication edge case had been checked.

The evidence is in:
- `tests/test_review_no_credentials.py`
- `review/01_test_fails_before_patch.txt`
- `review/03_test_passes_after_patch.txt`
- `review/04_full_suite_after_patch.txt`

One traceability mistake remained: after the patch was committed, rerunning `git diff -- src/` produced an empty patch and overwrote `review/02_diff.patch`. I should have preserved the original patch or regenerated it from the commits instead.

## 19. C3 did not go exactly as expected

**Commit:** `531a756`

I worked on the finished-wrong demonstration using a deliberately truncated Cloudflare response. The goal was to show that an output could look complete while still being incorrect, and that an independent check should catch the problem.

One of my own commands ran `check_independent.py` without its required arguments. Instead of performing the check, it raised:

`IndexError: list index out of range`

That was a command-usage error, not evidence that the independent checker had found the intended defect.

I learned to distinguish a checker successfully detecting bad output from the checker failing to run. I should not count an exception caused by missing arguments as a successful independent verification.

The broader lesson from C3 was that I need to inspect the actual command, its inputs, and its output before claiming that a demonstration worked.

## 20. What remains unresolved

**Reference:** `SIGNOFF.md`, section "Not checked"; `GATE.md` section 9.11.

I am signing off only on the behavior I actually checked. The remaining gaps include:

1. I have not tested every possible URL format, especially URLs with embedded credentials. The current provider templates do not generate them, but the policy does not explicitly reject every such case.
2. I have not independently checked every redirect scenario at the policy layer. The HTTP transport uses `allow_redirects=False`, but that is not the same as proving every redirect-related boundary.
3. I have not tested every possible real Greenhouse or Lever response or future API change. Most of my verification used controlled offline cases.

I also want the successful independent-checker run, with its required arguments, to be clearly traceable before claiming that the C3 verification is complete.

## What I learned overall

The biggest lesson from this project was that I cannot judge correctness only by whether Claude finishes a task or whether a test suite turns green.

Several problems came from the process around the code: editing the wrong file, committing incomplete documentation, using the wrong Python environment, and trusting commit messages that did not match the files.

The most useful review was the `.netrc` credential test because I could reproduce a specific failure before the fix, understand why it happened, and verify that the same test passed afterward.

Claude helped me build and revise the system, but I still had to decide what the requirements meant, review the changes, check the evidence, and be clear about what remained unresolved.
