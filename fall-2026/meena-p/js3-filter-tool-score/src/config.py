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

# --- Filter numbers, rule set "v3" = FILTER.md as committed in 4923b21 (its header says v1) ----
# hand-set in FILTER.md v1 (4923b21), section 1.4
V3_CORE_ROLE_POINTS = 2      # hand-set in FILTER.md v1 (4923b21): 2 per R1-R4 rule matched
V3_R5_POINT = 1              # hand-set in FILTER.md v1 (4923b21): +1 for R5, only with an R1-R4 match
V3_TOPIC_POINT = 1           # hand-set in FILTER.md v1 (4923b21): +1 per T1-T5 rule matched (no cap stated)
V3_KEEP_THRESHOLD = 5        # hand-set in FILTER.md v1 (4923b21): keep if score >= 5
V3_CLOSE_CALL_SCORE = 4      # hand-set in FILTER.md v1 (4923b21): no exclusion and score 4
V3_CLOSE_CALL_BOUNDARY_RULES = frozenset({"X3", "X5"})  # hand-set in FILTER.md v1 (4923b21): or score >= 5
                                                        # rejected by a single X3 or X5
# sha256 of the FILTER.md text v3 implements. The MCP tool refuses to score if FILTER.md changes.
V3_FILTER_MD_SHA256 = "f526811d11e02a86d286c9808bb75b8bf3f38cadbd78dd331ca51c182cfb6000"  # FILTER.md rules from 4923b21; Version line, Persona, W1-W4 labels and change log edited by me 2026-11-25

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
