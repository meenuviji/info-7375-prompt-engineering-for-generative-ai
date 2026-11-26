"""Load JS2's saved raw board responses (data/raw/) into a flat list of postings.

Fields read (FILTER.md section 3): title, location, description.
- Greenhouse: title, location.name, content (entity-escaped HTML: unescaped, tags removed).
- Lever: text (the title), categories.location, descriptionPlain.
Missing title -> posting skipped and counted. Missing location -> "unknown", never inferred.
Missing description -> "" (the filter then returns CANNOT_TELL for a role-matched title).
Postings are deduplicated by (provider, id); the first one seen is kept.
"""

import html
import json
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

from . import config as cfg

RAW_NAME = re.compile(r"^(greenhouse|lever)_([A-Za-z0-9-]+)_attempt\d+\.body$")

# Tags after which a line break keeps words from separate blocks apart.
BLOCK_TAGS = frozenset({"br", "p", "div", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6",
                        "tr", "table", "section", "blockquote"})


@dataclass(frozen=True)
class Posting:
    provider: str
    board: str
    id: str
    title: str
    location: str
    description: str


@dataclass
class LoadReport:
    loaded: int = 0
    skipped_no_title: int = 0
    duplicates_dropped: int = 0


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)  # decodes &amp; &nbsp; etc. inside the HTML
        self.parts: list[str] = []

    def handle_data(self, data):
        self.parts.append(data)

    def handle_starttag(self, tag, attrs):
        if tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in BLOCK_TAGS:
            self.parts.append("\n")


def html_to_text(content: str | None) -> str:
    """Greenhouse content -> plain text. The API returns the HTML itself entity-escaped
    (&lt;div&gt;...), so unescape once to get real tags, then strip tags (which also
    decodes the entities inside the HTML)."""
    if not content:
        return ""
    parser = _TextExtractor()
    parser.feed(html.unescape(content))
    parser.close()
    text = "".join(parser.parts).replace("\xa0", " ")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def _clean(value) -> str:
    return value.strip() if isinstance(value, str) else ""


def parse_greenhouse(board: str, body: dict) -> list[dict]:
    out = []
    for job in body.get("jobs", []):
        location = job.get("location")
        out.append({
            "provider": "greenhouse",
            "board": board,
            "id": str(job.get("id", "")),
            "title": _clean(job.get("title")),
            "location": _clean(location.get("name")) if isinstance(location, dict) else "",
            "description": html_to_text(job.get("content")),
        })
    return out


def parse_lever(board: str, body: list) -> list[dict]:
    out = []
    for job in body:
        categories = job.get("categories")
        out.append({
            "provider": "lever",
            "board": board,
            "id": str(job.get("id", "")),
            "title": _clean(job.get("text")),
            "location": _clean(categories.get("location")) if isinstance(categories, dict) else "",
            "description": _clean(job.get("descriptionPlain")),
        })
    return out


def records_to_postings(records, report: LoadReport, keep_missing_title: bool = False) -> list[Posting]:
    """keep_missing_title=True keeps title-less postings (FILTER.md 4923b21: CANNOT_TELL)
    but still counts them in report.skipped_no_title; False skips them (old v1/v2)."""
    seen: set[tuple[str, str]] = set()
    postings = []
    for r in records:
        if not r["title"] and not keep_missing_title:
            report.skipped_no_title += 1
            continue
        if not r["title"]:
            report.skipped_no_title += 1  # counted; kept only because keep_missing_title is set
        key = (r["provider"], r["id"])
        if key in seen:
            report.duplicates_dropped += 1
            continue
        seen.add(key)
        postings.append(Posting(r["provider"], r["board"], r["id"], r["title"],
                                r["location"] or "unknown", r["description"]))
    report.loaded = len(postings)
    return postings


def load_postings(raw_dir=None, keep_missing_title: bool = False) -> tuple[list[Posting], LoadReport]:
    raw_dir = Path(raw_dir) if raw_dir is not None else cfg.PROJECT_ROOT / cfg.RAW_DIR
    records = []
    for path in sorted(raw_dir.glob("*.body")):
        m = RAW_NAME.match(path.name)
        if not m:
            raise ValueError(f"unexpected raw file name: {path.name}")
        provider, board = m.groups()
        body = json.loads(path.read_bytes())
        records += parse_greenhouse(board, body) if provider == "greenhouse" else parse_lever(board, body)
    report = LoadReport()
    return records_to_postings(records, report, keep_missing_title), report
