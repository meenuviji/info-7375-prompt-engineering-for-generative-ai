"""The single choke point for network and file access, and the permission policy.

Every network call goes through GuardedIO.send(), which calls
SecurityPolicy.validate_network_request(). Every file read goes through
SecurityPolicy.validate_file_read() (the board config also through
validate_config_path()), and every file write or directory creation goes through
SecurityPolicy.validate_file_write().

Policy (GATE.md 9.5, 9.9, 9.10). Every check is default deny: an operation is allowed
only if a rule below explicitly allows it. A denial raises PolicyViolation naming the rule.
- Network: GET only; HTTPS only; port 443 (or none given); host exactly
  boards-api.greenhouse.io or api.lever.co after URL parsing, never by substring or prefix.
- Files: every path is resolved to a real absolute path against the project root,
  following .. and symlinks, before it is checked. Containment is decided by path
  components (Path.is_relative_to), never by string prefix.
  Read: config/, output/, traces/. Write: output/, traces/. Write to config/ only with
  approve_config_write (the --approve-config-write flag). Anything else is denied, even
  with approval. An existing file under traces/ is never written again, except
  traces/checkpoint.json and files this run created itself.

Not enforced here: redirects are refused in fetch.py (allow_redirects=False). Credentials,
~/.netrc and proxy settings are out of scope for this step (BOUNDARY_TESTS.md row 15).
"""

import os
from pathlib import Path
from urllib.parse import urlsplit

from . import config as cfg

ALLOWED_HOSTS = frozenset({"boards-api.greenhouse.io", "api.lever.co"})
ALLOWED_METHODS = frozenset({"GET"})
ALLOWED_PORTS = frozenset({None, 443})
READ_FOLDERS = ("config", "output", "traces")
WRITE_FOLDERS = ("output", "traces")
APPROVAL_WRITE_FOLDER = "config"
CONFIG_FOLDER = "config"
TRACES_FOLDER = "traces"
REPLACEABLE_TRACE_FILE = "traces/checkpoint.json"


class PolicyViolation(Exception):
    """A validator refused an operation. `rule` names the rule that denied it."""

    def __init__(self, message: str, rule: str = "unspecified"):
        super().__init__(f"[{rule}] {message}")
        self.rule = rule


class SecurityPolicy:
    def __init__(self, root: Path | None = None, *, approve_config_write: bool = False):
        self.root = Path(root if root is not None else cfg.PROJECT_ROOT).resolve()
        self.approve_config_write = approve_config_write
        self._created: set[Path] = set()  # files this run's policy allowed to be created

    # --- helpers -------------------------------------------------------------
    def resolve(self, path) -> Path:
        """Real absolute path: relative paths against the project root; .. and symlinks followed."""
        p = Path(path)
        if not p.is_absolute():
            p = self.root / p
        return p.resolve()

    def _inside(self, resolved: Path, folder: str) -> bool:
        # The folder itself is not resolved, so a symlinked folder cannot widen the boundary.
        base = self.root / folder
        return resolved == base or resolved.is_relative_to(base)

    # --- network -------------------------------------------------------------
    def validate_network_request(self, method: str, url: str) -> None:
        if method not in ALLOWED_METHODS:
            raise PolicyViolation(f"method {method!r} is not allowed; only GET", "net.method-not-get")
        try:
            parts = urlsplit(url)
            host, port = parts.hostname, parts.port
        except (ValueError, TypeError, AttributeError) as e:
            raise PolicyViolation(f"cannot parse URL {url!r}: {e}", "net.unparseable-url") from e
        if parts.scheme != "https":
            raise PolicyViolation(f"scheme {parts.scheme!r} is not allowed; only https", "net.scheme-not-https")
        if host not in ALLOWED_HOSTS:
            raise PolicyViolation(f"host {host!r} is not on the allow-list", "net.host-not-allowed")
        if port not in ALLOWED_PORTS:
            raise PolicyViolation(f"port {port} is not allowed; only 443", "net.port-not-443")

    # --- files ---------------------------------------------------------------
    def validate_file_read(self, path) -> None:
        resolved = self.resolve(path)
        if any(self._inside(resolved, folder) for folder in READ_FOLDERS):
            return
        raise PolicyViolation(f"read of {resolved} is outside config/, output/, traces/",
                              "file.read-outside-allowed-folders")

    def validate_config_path(self, path) -> None:
        """The board config must resolve to a file inside config/ (GATE.md 9.10: loop-level)."""
        resolved = self.resolve(path)
        if resolved == self.root / CONFIG_FOLDER or not self._inside(resolved, CONFIG_FOLDER):
            raise PolicyViolation(f"config {resolved} is not inside config/", "file.config-path-outside-config")
        self.validate_file_read(path)

    def validate_file_write(self, path) -> None:
        resolved = self.resolve(path)
        if self._inside(resolved, TRACES_FOLDER):
            existing_file = resolved.exists() and not resolved.is_dir()
            if (existing_file and resolved not in self._created
                    and resolved != self.root / REPLACEABLE_TRACE_FILE):
                raise PolicyViolation(f"{resolved} already exists; traces are never overwritten",
                                      "file.trace-overwrite")
            if not resolved.exists():
                self._created.add(resolved)
            return
        if any(self._inside(resolved, folder) for folder in WRITE_FOLDERS):
            return
        if self._inside(resolved, APPROVAL_WRITE_FOLDER):
            if self.approve_config_write:
                return
            raise PolicyViolation(f"write to {resolved} needs --approve-config-write",
                                  "file.config-write-needs-approval")
        raise PolicyViolation(f"write to {resolved} is outside output/, traces/ and config/",
                              "file.write-outside-allowed-folders")


class GuardedIO:
    """All network and file I/O made by the agent. Each method asks the policy first."""

    def __init__(self, policy: SecurityPolicy):
        self.policy = policy

    # --- network -------------------------------------------------------------
    def send(self, transport, method: str, url: str, timeout: float, on_authorized=None):
        self.policy.validate_network_request(method, url)
        if on_authorized is not None:
            on_authorized()  # e.g. count the request, only once it is allowed
        return transport.get(url, timeout)

    # --- reads ---------------------------------------------------------------
    def exists(self, path: Path) -> bool:
        self.policy.validate_file_read(path)
        return Path(path).exists()

    def read_bytes(self, path: Path) -> bytes:
        self.policy.validate_file_read(path)
        return Path(path).read_bytes()

    def read_config(self, path: Path) -> bytes:
        self.policy.validate_config_path(path)
        return Path(path).read_bytes()

    # --- writes --------------------------------------------------------------
    def make_dirs(self, path: Path) -> None:
        # Ask about every directory that would be created, not just the last one.
        path = Path(path)
        missing = [p for p in (path, *path.parents) if not p.exists()]
        for p in reversed(missing):
            self.policy.validate_file_write(p)
            p.mkdir(exist_ok=True)

    def create_new(self, path: Path, data: bytes) -> None:
        """Create a file that must not exist yet. Never overwrites (FileExistsError)."""
        self.policy.validate_file_write(path)
        with open(path, "xb") as f:
            f.write(data)

    def append_text(self, path: Path, text: str) -> None:
        self.policy.validate_file_write(path)
        with open(path, "a", encoding="utf-8") as f:
            f.write(text)

    def replace_atomic(self, path: Path, data: bytes) -> None:
        """Replace a file in one step (temp file + os.replace). Used for state and checkpoint."""
        path = Path(path)
        tmp = path.with_name(f".{path.name}.tmp-{os.getpid()}")
        self.policy.validate_file_write(tmp)
        self.policy.validate_file_write(path)
        with open(tmp, "xb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
