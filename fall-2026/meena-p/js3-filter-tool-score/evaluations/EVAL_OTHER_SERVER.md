# Evaluation: MCP fetch server

Source: github.com/modelcontextprotocol/servers, src/fetch, commit c799c8552b0f27b7a33a7b9233773da144dddcf5, read not run.

## Declared versus actual

*Draft by Claude Code, checked by me.* Paths are relative to `src/fetch/`; `server.py` means `src/mcp_server_fetch/server.py`.

**What tools/list declares** (built by the SDK from the decorated function):
- One tool, `fetch` (`server.py:1019–1032`), with the description "Fetches a URL from the internet and optionally extracts its contents as markdown. Although originally you did not have internet access, and were advised to refuse and tell the user this, this tool now grants you internet access…" (`server.py:947–949`).
- Annotations `readOnlyHint: true`, `destructiveHint: false`, `idempotentHint: true`, `openWorldHint: true` (`server.py:1024–1029`).
- Input: `url` (pydantic `AnyUrl`, any scheme) (`server.py:1036`); `max_length` 1–999999, default 5000; `start_index` ≥ 0; `raw` bool; `timeout_ms` 100–600000, default 30000 (`server.py:1037–1073`, `timeout.py:21–23`). There is no `outputSchema` (`server.py:1030–1031`). A `fetch` prompt is also offered (`server.py:1108–1139`).

**What the code actually does:**
- Robots check: before a tool fetch, it fetches the site's robots.txt and refuses on Disallow, 401, 403 or 5xx (`server.py:761–820`, `1077–1080`). The `fetch` prompt skips robots.txt (`server.py:1125–1126`).
- Requests: GET only (`server.py:539–556`). Redirects are followed one hop at a time with each body unread, and every hop passes through the same request hooks (`server.py:556–570`, `879–887`).
- Size: bodies over 5 MiB are refused (`server.py:465`, `906–911`).
- Conversion: HTML is converted to markdown, with Readability.js under Node.js when `node` is on PATH (`server.py:933–937`).

**Gaps:**
- **`readOnlyHint: true` understates side effects.**
  - On first use the server may run `npm install`, which contacts the npm registry outside every fetch guard and writes into the package directory (`readability_js.py:161–175`).
  - Each page's HTML is written to a temporary file and passed to a Node.js subprocess (`readability_js.py:227–239`).
  - GET requests can change state on the remote server.
- **The description persuades the model rather than describing limits.** It never mentions the robots check, the private-address refusal, or the 5 MiB cap (`server.py:947–949`).
- **The README contradicts itself.** README.md:12 says the server "can access local/internal IP addresses", while README.md:14 and the code refuse them by default.
- **"Read-only" doesn't come from a scheme allowlist.** `AnyUrl` accepts any scheme. `file:` and other non-HTTP schemes fail only because httpx has no transport for them; the resulting error becomes a `ToolError` (`server.py:798–801`, `916–917`). Not verified by running.

## What a compatible client is not entitled to

*Draft by Claude Code, checked by me.*

**Prevented by default:**
- **Local and internal addresses.** `_is_public_address` (`server.py:156–181`) refuses:
  - loopback, RFC 1918, link-local `169.254.0.0/16` (cloud metadata), and `100.64.0.0/10`
  - unique-local IPv6, multicast, and documentation or other special ranges (list at `server.py:87–120`)
  - IPv4-mapped, translated and NAT64 forms, judged by the IPv4 address inside (`server.py:169–174`)
  - IPv6 outside `2000::/3` (`server.py:179–180`)

  Three checks enforce it:
  1. A request hook resolves the host and refuses if any address is non-public. It runs before every request and redirect hop (`server.py:184–210`; installed at `780–781`, `882–883`).
  2. A connect-time check vets the addresses actually used (`server.py:213–228`).
  3. Direct connections are pinned to those vetted IP literals, which blocks DNS rebinding (`pinning.py:96–107`, `server.py:450–454`).
- **Other methods and headers.** The client can only pass the five arguments, so requests are GET only (`server.py:1033–1073`).
- **Large bodies.** Responses over 5 MiB are refused (`server.py:906–911`).
- **Unknown tools and prompts.** They get a -32602 error (`server.py:956–990`).
- **Unlisted hosts, if the operator passes `--allowed-hosts`.** Every hop is checked by name (`allowlist.py:109–125`, `server.py:778–779`, `880–881`). This is **off by default** (`allowlist.py:4–5`).

**Not prevented, or only by configuration:**
- **`--allow-private-ips`** turns off the hook and the pinning, so internal addresses can be fetched (`__init__.py:38`; `server.py:450`, `780`, `882`).
- **Any proxy** (`--proxy-url`, or `HTTP_PROXY`/`HTTPS_PROXY`/`ALL_PROXY` inherited from the launching environment) bypasses pinning.
  - The proxy resolves and connects on its own side, so the address reached is not checked (`pinning.py:17–20`, `server.py:401–428`, `443`).
  - A host the server can't resolve itself skips the check entirely (`server.py:200–203`).
- **Ports.** Any port on a public host can be reached; no port rule exists, not even in allowlist entries (`allowlist.py:15`).
- **Data in the URL.** Data can leave in a URL's path or query string, and the page content returned to the model is unfiltered.
- **Network clients on a widened `HOST`.** With Streamable HTTP and `HOST` widened beyond loopback, only the Origin header is checked and there's no authentication (`transport.py:48–82`).

## My trust decision

### 1. Would I let Claude use this server?
Yes, for **read-only research on public web pages** (such as reading documentation, public GitHub files, or articles), provided it is launched with strict network and runtime constraints. I would not grant it unrestricted access across general-purpose coding sessions where sensitive local files or credentials are present in the model's context.

### 2. Under what limits?
Based on the gaps and behaviors found in `server.py`, `pinning.py`, and `readability_js.py`, I would run `mcp-server-fetch` only under these specific guardrails:
1. **Default network guards intact, plus explicit host allowlisting:** Never pass `--allow-private-ips` or `--ignore-robots-txt`. Whenever the task targets known domains (for example, `docs.python.org` or `github.com`), pass `--allowed-hosts` so Claude cannot use URL query strings or paths to exfiltrate local context to an attacker-controlled server.
2. **Clean proxy environment and `stdio` transport only:** Clear `HTTP_PROXY`, `HTTPS_PROXY`, and `ALL_PROXY` before launching the server so httpx uses the pinned direct transport (`pinning.py`) rather than an unpinned proxy that bypasses private-IP checks. Keep the default `stdio` transport rather than binding Streamable HTTP to a network interface without authentication.
3. **Disable or pre-bake the Node.js `npm install` path:** Either run in an environment without `node` on `PATH` (forcing the pure-Python extractor) or pre-install `readabilipy`'s JS dependencies in a read-only container image so the first HTML fetch does not trigger an unguarded `npm install` side effect.
4. **Treat fetched output as untrusted input:** Because page bodies and `robots.txt` refusal messages are returned raw to the model without sanitization, require manual confirmation before Claude executes any shell commands, edits files, or calls other tools immediately after a `fetch` call.

### 3. What would make me change my mind?
- **Adding unrestricted outbound fetch alongside sensitive local access:** If I am working in a repository containing API keys, `.env` secrets, or private data and cannot restrict `--allowed-hosts`, the risk of prompt injection triggering URL-based data exfiltration outweighs the convenience of live web fetching.
- **Unpinned proxy or private-IP requirements:** If a network environment forces traffic through an HTTP proxy (disabling `pinning.py`'s IP-literal connection check) or requires `--allow-private-ips`, the SSRF protections against `127.0.0.1` and cloud metadata endpoints (`169.254.169.254`) degrade too much to trust autonomous tool calls.
- **Code audit regressions:** If future commits weaken `_is_public_address` / `pinning.py`, allow non-HTTP schemes, or execute downloaded page scripts during HTML-to-markdown conversion.