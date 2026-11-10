"""Fixed constants for JS2.

Budgets are set by Meena Periasamy only (GATE.md section 3). The loop never changes
them. Tests may pass different budgets into run_agent() to reach a limit; the CLI
cannot.
"""

from pathlib import Path
from types import MappingProxyType

# Every path resolves against this root, never the current directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# --- Budgets -------------------------------------------------------------------
MAX_SECONDS = 60.0   # GATE.md 9.2
MAX_REQUESTS = 12    # GATE.md 9.2
MAX_BOARDS = 5       # GATE.md 9.2 (boards in 9.7)

BUDGETS = MappingProxyType({
    "max_seconds": MAX_SECONDS,
    "max_requests": MAX_REQUESTS,
    "max_boards": MAX_BOARDS,
})

# Real boards: 10 s per request, shortened to the seconds left in the budget (GATE.md 9.2, 9.9).
# A board may set its own "timeout" in the config (the deliberate timeout board uses 0.001).
REQUEST_TIMEOUT_SECONDS = 10.0

# --- Exit codes (GATE.md section 2) ---------------------------------------------
EXIT_CODES = MappingProxyType({
    "SUCCESS": 0,
    "FATAL_SYSTEM_ERROR": 1,
    "PARTIAL_SUCCESS": 2,
    "BUDGET_EXCEEDED": 3,
})

# --- Providers -------------------------------------------------------------------
PROVIDER_URLS = MappingProxyType({
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true",
    "lever": "https://api.lever.co/v0/postings/{token}?mode=json",
})

# --- Paths (relative to the project root) ----------------------------------------
DEFAULT_CONFIG = "config/boards.json"
RAW_DIR = "output/raw"                 # output/raw/<run_id>/
STATES_DIR = "output/states"           # output/states/<board_token>.json (GATE.md 5.1)
TRACES_DIR = "traces"                  # traces/trace_<run_id>.jsonl
MALFORMED_DIR = "traces/malformed"
CHECKPOINT_PATH = "traces/checkpoint.json"  # latest-run pointer, replaced atomically

# --- Error policy -----------------------------------------------------------------
# kind -> what the loop does. "code" is the error_code recorded when the board fails
# (for retryable kinds, after the retries are used up). GATE.md 9.9: each retryable
# kind is retried once, after a single fixed wait of base_wait seconds (1.5 s or 2.0 s),
# not repeated backoff. Every retry is a real request and counts against max_requests.
ERROR_POLICY = MappingProxyType({
    "TIMEOUT":               {"retry": True,  "max_retries": 1, "base_wait": 1.5, "code": "TIMEOUT_EXHAUSTED"},
    "HTTP_5XX":              {"retry": True,  "max_retries": 1, "base_wait": 2.0, "code": "UPSTREAM_5XX_ERROR"},
    "HTTP_429":              {"retry": True,  "max_retries": 1, "base_wait": 2.0, "code": "RATE_LIMITED_EXHAUSTED"},
    "HTTP_404":              {"retry": False, "code": "BOARD_NOT_FOUND"},
    "HTTP_3XX":              {"retry": False, "code": "REDIRECT_REFUSED"},
    "HTTP_OTHER":            {"retry": False, "code": "HTTP_ERROR"},
    "CONNECTION_ERROR":      {"retry": False, "code": "NETWORK_ERROR"},
    "REQUEST_ERROR":         {"retry": False, "code": "NETWORK_ERROR"},
    "TRANSPORT_EXCEPTION":   {"retry": False, "code": "TRANSPORT_EXCEPTION"},
    "SUSPICIOUS_PAYLOAD":    {"retry": False, "code": "SUSPICIOUS_PAYLOAD"},
    "TRUNCATED_RESPONSE":    {"retry": False, "code": "TRUNCATED_RESPONSE"},
    "PARSE_SCHEMA_MISMATCH": {"retry": False, "code": "PARSE_SCHEMA_MISMATCH"},
})

REQUIRED_POLICY_KINDS = frozenset(ERROR_POLICY)
