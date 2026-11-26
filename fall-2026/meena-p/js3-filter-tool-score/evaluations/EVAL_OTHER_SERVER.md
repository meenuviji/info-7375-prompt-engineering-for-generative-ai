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