"""US-eligibility of a posting's location, for FILTER.md rule X3 and section 3.

Decision (Meena Periasamy, 2026-11-25): use the location field; if it names no place
(e.g. "Hybrid", "Distributed", "In-Office"), use the description's
"Available Location(s):" line; if neither names a place, the location is AMBIGUOUS.

A text is US when it contains (FILTER.md X3: "a US state/city, united states, usa, u.s.,
or US-eligible remote"):
- "united states", "usa", "u.s." / "u.s.a." (case-insensitive), or "US" as a capitalised word;
- a US state name, "district of columbia", or "D.C.";
- a two-letter state code after a comma (", NY") or at the start ("OH (remote within the
  state)"), case-sensitive;
- a city in US_CITIES (a short hand-made list; it is not exhaustive — see below).
"Remote" counts as US only together with one of the signals above (e.g. "California, USA,
Remote"); "Remote" alone, "North America", "Hybrid", "Distributed" and "In-Office" are not
place names. A text that names a place but has no US signal is NON_US (X3 fires).

US_CITIES is a judgment call made while implementing, not a rule from FILTER.md: it lists
US cities that appear without a state in these boards' location text. A US city missing
from it would be classified NON_US; run_filter.py --version v3 prints every NON_US
location string so they can be checked.
"""

import re

US = "US"
NON_US = "NON_US"
AMBIGUOUS = "AMBIGUOUS"

STATES = ["alabama", "alaska", "arizona", "arkansas", "california", "colorado", "connecticut", "delaware",
          "florida", "georgia", "hawaii", "idaho", "illinois", "indiana", "iowa", "kansas", "kentucky",
          "louisiana", "maine", "maryland", "massachusetts", "michigan", "minnesota", "mississippi",
          "missouri", "montana", "nebraska", "nevada", "new hampshire", "new jersey", "new mexico",
          "new york", "north carolina", "north dakota", "ohio", "oklahoma", "oregon", "pennsylvania",
          "rhode island", "south carolina", "south dakota", "tennessee", "texas", "utah", "vermont",
          "virginia", "washington", "west virginia", "wisconsin", "wyoming", "district of columbia"]
STATE_CODES = ["AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL", "IN", "IA", "KS",
               "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY",
               "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV",
               "WI", "WY", "DC"]
# Judgment call (see module docstring): US cities that appear without a state in these boards.
US_CITIES = ["austin", "san francisco", "new york city", "nyc", "seattle", "boston", "denver", "chicago",
             "palo alto", "miami", "atlanta", "los angeles", "san diego", "san jose", "pittsburgh", "honolulu"]

# Words that say how or where-ish someone works without naming a place.
NOT_A_PLACE = ["hybrid", "distributed", "in-office", "in office", "remote", "north america", "onsite",
               "on-site", "or", "and", "flexible"]

_US_WORDS = re.compile(r"\b(?:united states|usa)\b|\bu\.s\.(?:a\.)?|\b(?:" + "|".join(STATES + US_CITIES)
                       + r")\b|\bd\.c\.", re.IGNORECASE)
_US_CASED = re.compile(r"\bUS\b|(?:,\s*|^\s*)(?:" + "|".join(STATE_CODES) + r")\b")
_NOT_A_PLACE = re.compile(r"\b(?:" + "|".join(re.escape(w) for w in NOT_A_PLACE) + r")\b", re.IGNORECASE)
_AVAILABLE = re.compile(r"^\s*Available Locations?\s*[-:–]\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)


def classify_text(text: str) -> str:
    text = (text or "").strip()
    if _US_WORDS.search(text) or _US_CASED.search(text):
        return US
    leftover = re.sub(r"[^A-Za-z]+", " ", _NOT_A_PLACE.sub(" ", text)).strip()
    return NON_US if leftover else AMBIGUOUS


def classify(location: str, description: str) -> tuple[str, str]:
    """Return (US | NON_US | AMBIGUOUS, the text that decided it)."""
    from_field = classify_text(location if location != "unknown" else "")
    if from_field != AMBIGUOUS:
        return from_field, location
    m = _AVAILABLE.search(description or "")
    if m:
        from_line = classify_text(m.group(1))
        if from_line != AMBIGUOUS:
            return from_line, m.group(1)
    return AMBIGUOUS, location
