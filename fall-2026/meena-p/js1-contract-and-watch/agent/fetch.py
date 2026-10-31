"""Allow-listed fetch of the Greenhouse board. Raw responses are saved unmodified."""

import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

ALLOWED_HOSTS = frozenset({"boards-api.greenhouse.io"})
BOARD_URL = "https://boards-api.greenhouse.io/v1/boards/cloudflare/jobs?content=true"
RAW_DIR = Path("evidence/raw")


class HostNotAllowedError(Exception):
    pass


def check_allowed(url: str) -> None:
    """Raise HostNotAllowedError unless url is https on an allow-listed host."""
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise HostNotAllowedError(f"host not on allow-list: {parsed.hostname!r} ({url})")


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def safe_label(label: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", label):
        raise ValueError(f"label must match [A-Za-z0-9_-]+: {label!r}")
    return label


def fetch_board(label: str, url: str = BOARD_URL, raw_dir: Path = RAW_DIR) -> Path:
    """Fetch url and write the response body byte-for-byte to raw_dir. Returns the saved path."""
    check_allowed(url)  # before any network call
    safe_label(label)
    # Redirects are not followed: a 3xx could lead off the allow-list, so it is an error.
    resp = requests.get(url, timeout=30, allow_redirects=False)
    if 300 <= resp.status_code < 400:
        raise HostNotAllowedError(
            f"redirect refused: {resp.status_code} to {resp.headers.get('Location')!r}")
    resp.raise_for_status()
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / f"{utc_timestamp()}_{label}.json"
    path.write_bytes(resp.content)
    return path


if __name__ == "__main__":
    # Fetch-only: save a raw response without touching state.
    label = sys.argv[1] if len(sys.argv) > 1 else "live"
    print(fetch_board(label))
