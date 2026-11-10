"""The single choke point for network and file access.

Every network call goes through GuardedIO.send(), which calls
SecurityPolicy.validate_network_request(). Every file read goes through
SecurityPolicy.validate_file_read(), and every file write or directory creation goes
through SecurityPolicy.validate_file_write().

NOT YET MEETING GATE.md: the three validators below allow everything. GATE.md
requires default-deny enforcement. Meena Periasamy will specify that behavior next.
Until then, nothing here protects the network or the filesystem.
"""

import os
from pathlib import Path


class PolicyViolation(Exception):
    """Raised by a validator to refuse an operation. Stops the run as FATAL_SYSTEM_ERROR."""


class SecurityPolicy:
    def validate_network_request(self, method: str, url: str) -> None:
        # NOT YET MEETING GATE.md: allows every method, scheme, host and port.
        # GATE.md requires default-deny. (JS1's host allow-list in fetch.py was removed
        # so that this method is the only place where the decision is made.)
        return None

    def validate_file_read(self, path: Path) -> None:
        # NOT YET MEETING GATE.md: allows reading any path.
        return None

    def validate_file_write(self, path: Path) -> None:
        # NOT YET MEETING GATE.md: allows writing any path. No Path.resolve()
        # containment check, no symlink check, no ./output/ or ./traces/ boundary.
        return None


class GuardedIO:
    """All network and file I/O made by the agent. Each method asks the policy first."""

    def __init__(self, policy: SecurityPolicy):
        self.policy = policy

    # --- network -------------------------------------------------------------
    def send(self, transport, method: str, url: str, timeout: float):
        self.policy.validate_network_request(method, url)
        return transport.get(url, timeout)

    # --- reads ---------------------------------------------------------------
    def exists(self, path: Path) -> bool:
        self.policy.validate_file_read(path)
        return Path(path).exists()

    def read_bytes(self, path: Path) -> bytes:
        self.policy.validate_file_read(path)
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
