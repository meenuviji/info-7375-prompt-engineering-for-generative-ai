"""Network transport for JS2. Base: the_contract_watch agent/fetch.py (JS1).

Kept from JS1: redirects are never followed (a 3xx could lead elsewhere; the loop
records it as REDIRECT_REFUSED), the body is kept byte-for-byte, labels must match
[A-Za-z0-9_-]+, and timestamps are UTC.

Changed for JS2:
- The transport only performs the request and returns status + raw bytes. Saving,
  validation and retries are the loop's job.
- The host allow-list (JS1 check_allowed) moved to SecurityPolicy.validate_network_request,
  which is currently an allow-everything stub (see src/policy.py).
- Every requests exception is mapped to a TransportError kind so that no board
  failure escapes as a traceback.
- The timeout is supplied per call by the loop (10 s, capped at the budget remaining).
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class Response:
    status: int
    body: bytes
    headers: dict = field(default_factory=dict)


class TransportError(Exception):
    """A request that produced no HTTP response. kind is a key of config.ERROR_POLICY."""

    def __init__(self, kind: str, detail: str):
        super().__init__(f"{kind}: {detail}")
        self.kind = kind
        self.detail = detail


def utc_timestamp() -> str:
    # Microseconds so that two runs in the same second never share a trace or raw directory.
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def safe_label(label: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", label):
        raise ValueError(f"label must match [A-Za-z0-9_-]+: {label!r}")
    return label


class RequestsTransport:
    """Live HTTP transport. Only reached when the agent is run from the CLI."""

    def get(self, url: str, timeout: float) -> Response:
        import requests  # imported here so tests never load the live transport

        try:
            resp = requests.get(url, timeout=timeout, allow_redirects=False)
            return Response(resp.status_code, resp.content, dict(resp.headers))
        except requests.Timeout as e:  # ConnectTimeout and ReadTimeout; checked before ConnectionError
            raise TransportError("TIMEOUT", repr(e)) from e
        except requests.ConnectionError as e:
            raise TransportError("CONNECTION_ERROR", repr(e)) from e
        except requests.RequestException as e:
            raise TransportError("REQUEST_ERROR", repr(e)) from e
