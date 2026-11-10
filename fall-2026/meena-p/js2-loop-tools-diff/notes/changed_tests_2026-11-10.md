2026-11-10

Raw Claude Code response, saved unedited

No assert line was removed or modified in either test; `git diff tests/test_loop.py` changes only the test name, the `Refuse` override, the two policy constructor calls, and adds one assert. But the old Refuse property is no longer tested in its original form, and one of its kept asserts now proves less. Details below.

## 1. The old Refuse test

Old name `test_fatal_exit_1_when_a_policy_validator_refuses`, now `test_fatal_exit_1_when_the_policy_refuses_a_loop_file_write`.

**(1) What it protected.** If the network validator refuses a request, the run stops as `FATAL_SYSTEM_ERROR` (exit 1, subsystem `security_policy`), and no request reaches the transport. Behind that sits the more general property: a policy denial is never swallowed or turned into a value.

**(2) Why it was wrong under 9.10.** 9.10 makes a network denial a board failure: `POLICY_DENIED`, the run continues, and it ends `PARTIAL_SUCCESS` (exit 2). The old `exit_code == 1` contradicts that. After the policy was implemented, the test was also passing for the wrong reason. `Refuse()` defaulted to the real project root, so reading the sandbox config was denied, and the run ended with exit 1 before any network check ran.

**(3) What protects the original property now.**
- *"A network refusal ends the run with exit 1"* is withdrawn on purpose by 9.10. Nothing protects it, and nothing should.
- *"A refused request never reaches the transport, and the denial is recorded, not swallowed"*: `test_boundary_17_board_on_disallowed_host_in_config`. It checks that no example.com call was made, that `requests_used == 2`, `POLICY_DENIED` with a `null` count, a failed ledger entry, and a trace line with `request_sent: false` and `denied_rule: net.host-not-allowed`.
- *"A denial of a loop-level operation is exit 1 with subsystem `security_policy`"*: the renamed test (a refused file write) and `test_boundary_16_config_path_outside_config` (a refused config read).
- **Gap:** no test has a network validator refusing a request that the real policy would allow. Nor does any test cover a run where every board is denied (expected: all `POLICY_DENIED`, zero transport calls, exit 2). `test_boundary_17` covers one denied board, through the real host rule.

**(4) Did any assertion become looser?** No assert line was removed or modified. All three old asserts are still present, word for word:
```python
self.assertEqual(report["exit_code"], 1)
self.assertEqual(report["error"]["subsystem"], "security_policy")
self.assertEqual(self.sb.transport.calls, [])
```
One assert was added:
```python
self.assertEqual(report["error"]["denied_rule"], "test.refuse-writes")
```
In substance, though, `self.assertEqual(self.sb.transport.calls, [])` now proves less. In the old test, every file operation was allowed, so the empty call list showed that the network refusal itself stopped the request. In the new test, the run dies at its first file write (creating the trace), which comes before the loop reaches any board. So the empty list is guaranteed and says nothing about network handling. The lines that changed, none of them asserts:
```python
-    def test_fatal_exit_1_when_a_policy_validator_refuses(self):
-            def validate_network_request(self, method, u):
-                raise PolicyViolation("refused for test")
-        report = self.sb.run(REAL_OK, policy=Refuse())
```

## 2. IORouting (`test_all_io_passes_through_the_policy`)

**(1) What it protected.** All I/O goes through the policy: every transport call is preceded by `validate_network_request` for the same URL, every file and folder under `output/` and `traces/` passed through `validate_file_write`, and the config read passed through `validate_file_read`.

**(2) Why it broke.** It was not because of 9.10's denial handling; my earlier summary grouped it under 9.10 too loosely. It broke because of the new config-path rule (`--config` must resolve inside `config/`, a loop-level denial per 9.10). `SecurityPolicy` now needs the project root for that check. `Recording()` defaulted to the real project root, so the sandbox config was denied, the run stopped before any I/O, and `events` was empty.

**(3) What protects the property now.** The same test, `IORouting.test_all_io_passes_through_the_policy`, with the sandbox root passed in.

**(4) Did any assertion become looser?** No. All three asserts are unchanged:
```python
self.assertEqual(nets, [u for u, _ in self.sb.transport.calls])
self.assertIn(path.resolve(), written, f"{path} was written without validate_file_write")
self.assertIn(("read", (self.sb.root / self.sb.config).resolve()), events)
```
The only changed line:
```python
-        self.sb.run(dict(REAL_OK, **{CF: [ok("html_challenge.html")]}), policy=Recording())
+        self.sb.run(dict(REAL_OK, **{CF: [ok("html_challenge.html")]}), policy=Recording(self.sb.root))
```
One limit, which is not new: `Recording` overrides the three validators, so this test proves the routing, not the rules. The real rules are tested by the boundary tests. The config read now also goes through the inherited real `validate_config_path`, which calls `Recording.validate_file_read`, so the read assert still sees it.
