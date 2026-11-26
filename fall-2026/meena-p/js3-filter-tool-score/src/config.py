"""Fixed constants for JS3. Nothing here is fitted on data."""

from pathlib import Path

# Every path resolves against the project root, never the current directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# --- Filter numbers ---------------------------------------------------------------
# hand-set in FILTER.md v1 (section 1.4)
ROLE_SCORE = 3            # hand-set in FILTER.md v1: base score if any role rule R1-R5 matches the title
TOPIC_POINT = 1           # hand-set in FILTER.md v1: +1 per distinct topic rule T1-T5 matching the description
TOPIC_CAP = 4             # hand-set in FILTER.md v1: topic part capped at 4 points (W2)
KEEP_THRESHOLD = 5        # hand-set in FILTER.md v1: keep when score >= 5
CLOSE_CALL_SCORES = frozenset({4, 5})  # hand-set in FILTER.md v1: close-call window, score 4 or 5

# --- Labeling-set sampling ----------------------------------------------------------
# Set in the JS3 build instructions (2026-11-25), not in FILTER.md.
SEED = 20261125
SET_A_REJECTED = 30
SET_A_CLOSE_CALLS = 5
SET_A_KEPT = 5
SET_B_SIZE = 30

# --- Paths (relative to the project root) --------------------------------------------
RAW_DIR = "data/raw"
RESULTS_CSV = "output/filter_results.csv"
LABELS_DIR = "labels"

# --- Decisions -------------------------------------------------------------------------
KEPT = "KEPT"
REJECTED = "REJECTED"
CANNOT_TELL = "CANNOT_TELL"
DECISIONS = (KEPT, REJECTED, CANNOT_TELL)
