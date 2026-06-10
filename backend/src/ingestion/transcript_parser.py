"""
Transcript parser for SEC EDGAR earnings call filings.

EDGAR filings come in messy HTML/SGML with no consistent structure.
Different companies format their transcripts differently. This parser
handles the most common patterns:

    1. Speaker names in bold (<b>, <strong>) followed by content
    2. Speaker names with roles in parentheses: "Tim Cook - CEO"
    3. Section headers like "Prepared Remarks" and "Q&A"
    4. Various separator patterns between speakers

The parser works in stages:
    - Clean the raw HTML (strip tags, normalize whitespace)
    - Detect section boundaries (prepared remarks vs Q&A)
    - Extract individual speaker turns with name and role detection
    - Classify speakers into roles (CEO, CFO, analyst, etc.)
"""

import logging
import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


# Patterns used to identify section boundaries
PREPARED_REMARKS_PATTERNS = [
    r"prepared\s+remarks",
    r"opening\s+remarks",
    r"presentation",
    r"management\s+discussion",
    r"management\s+commentary",
]

QA_SECTION_PATTERNS = [
    r"question[\s-]*and[\s-]*answer",
    r"q\s*&\s*a\s+session",
    r"q\s*&\s*a",
    r"questions?\s+and\s+answers?",
    r"analyst\s+questions",
]

# Patterns for identifying speaker lines
SPEAKER_PATTERNS = [
    # "Name -- Title, Company" or "Name - Title"
    re.compile(
        r"^([A-Z][a-zA-Z\.\'\-\s]{2,40})\s*[\-\u2013\u2014]{1,3}\s*(.+?)$",
        re.MULTILINE,
    ),
    # "Name (Title):" or "Name, Title:"
    re.compile(
        r"^([A-Z][a-zA-Z\.\'\-\s]{2,40})\s*[\(,]\s*(.+?)[\):]",
        re.MULTILINE,
    ),
    # "Name:" at start of line (fallback, no role)
    re.compile(
        r"^([A-Z][a-zA-Z\.\'\-\s]{2,40})\s*:\s*$",
        re.MULTILINE,
    ),
]

# Keywords that indicate a speaker's role
ROLE_KEYWORDS = {
    "ceo": [
        "chief executive", "ceo", "president and ceo",
        "chairman and ceo", "president & ceo",
    ],
    "cfo": [
        "chief financial", "cfo", "finance officer",
        "senior vice president, finance",
    ],
    "coo": ["chief operating", "coo"],
    "cto": ["chief technology", "cto", "chief technical"],
    "executive": [
        "president", "vice president", "svp", "evp",
        "executive vice", "senior vice", "head of",
        "director", "general manager", "managing director",
    ],
    "analyst": [
        "analyst", "research", "securities", "capital",
        "morgan stanley", "goldman sachs", "jpmorgan",
        "barclays", "citi", "bank of america", "wells fargo",
        "ubs", "deutsche bank", "credit suisse", "rbc capital",
        "td securities", "bmo capital", "scotia",
    ],
    "operator": ["operator", "conference facilitator"],
}


@dataclass
class SpeakerTurn:
    """A single speaker's continuous remarks."""

    speaker_name: str
    speaker_role: str
    content: str
    section_type: str  # prepared_remarks, qa, unknown
    turn_index: int = 0


@dataclass
class ParsedTranscript:
    """A fully parsed earnings call transcript."""

    company_name: str
    quarter: str
    year: int
    speakers: list[str] = field(default_factory=list)
    turns: list[SpeakerTurn] = field(default_factory=list)
    raw_text: str = ""


def clean_html(html_content: str) -> str:
    """
    Strip HTML tags and normalize whitespace.

    Preserves paragraph boundaries by converting block elements
    to newlines before stripping all tags.
    """
    soup = BeautifulSoup(html_content, "lxml")

    # Remove script and style elements
    for tag in soup(["script", "style", "head"]):
        tag.decompose()

    # Convert block elements to newlines for paragraph detection
    for tag in soup.find_all(["p", "div", "br", "tr", "li", "h1", "h2", "h3", "h4"]):
        tag.insert_before("\n")
        tag.insert_after("\n")

    text = soup.get_text()

    # Normalize whitespace while preserving paragraph breaks
    lines = []
    for line in text.split("\n"):
        cleaned = " ".join(line.split())
        if cleaned:
            lines.append(cleaned)

    return "\n".join(lines)


def detect_section_type(text: str) -> str:
    """
    Determine if a block of text is from prepared remarks or Q&A.

    Looks for section header patterns that typically appear
    before each section of an earnings call transcript.
    """
    text_lower = text.lower()

    for pattern in QA_SECTION_PATTERNS:
        if re.search(pattern, text_lower):
            return "qa"

    for pattern in PREPARED_REMARKS_PATTERNS:
        if re.search(pattern, text_lower):
            return "prepared_remarks"

    return "unknown"


def classify_speaker_role(name: str, role_text: str) -> str:
    """
    Classify a speaker into a role category.

    Uses the role text (title/description) that appears after
    the speaker's name in the transcript. Falls back to keyword
    matching in the name itself.

    Args:
        name: Speaker's name
        role_text: Title or description text after the name

    Returns:
        One of: ceo, cfo, coo, cto, executive, analyst, operator, unknown
    """
    combined = f"{name} {role_text}".lower()

    for role, keywords in ROLE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in combined:
                return role

    return "unknown"


def extract_speaker_turns(text: str) -> list[SpeakerTurn]:
    """
    Extract individual speaker turns from cleaned transcript text.

    Walks through the text looking for speaker name patterns.
    Everything between two speaker patterns belongs to the first speaker.
    Also tracks which section (prepared remarks vs Q&A) each turn
    falls in based on section header detection.

    Args:
        text: Cleaned transcript text (HTML already stripped)

    Returns:
        List of SpeakerTurn objects in order of appearance
    """
    lines = text.split("\n")
    turns: list[SpeakerTurn] = []
    current_speaker = ""
    current_role = "unknown"
    current_section = "prepared_remarks"  # Calls typically start with prepared remarks
    current_content_lines: list[str] = []
    turn_index = 0

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Check for section boundary
        section = detect_section_type(stripped)
        if section != "unknown":
            current_section = section
            continue

        # Check if this line is a speaker identifier
        speaker_found = False
        for pattern in SPEAKER_PATTERNS:
            match = pattern.match(stripped)
            if match:
                # Save the previous speaker's turn
                if current_speaker and current_content_lines:
                    content = " ".join(current_content_lines).strip()
                    if len(content) > 20:  # Skip very short turns (e.g. "Thank you")
                        turns.append(
                            SpeakerTurn(
                                speaker_name=current_speaker.strip(),
                                speaker_role=current_role,
                                content=content,
                                section_type=current_section,
                                turn_index=turn_index,
                            )
                        )
                        turn_index += 1

                # Start new speaker
                current_speaker = match.group(1).strip()
                role_text = match.group(2).strip() if match.lastindex and match.lastindex >= 2 else ""
                current_role = classify_speaker_role(current_speaker, role_text)
                current_content_lines = []

                # If there is content on the same line after the pattern
                remaining = stripped[match.end():].strip()
                if remaining:
                    current_content_lines.append(remaining)

                speaker_found = True
                break

        if not speaker_found and current_speaker:
            current_content_lines.append(stripped)

    # Save the last speaker's turn
    if current_speaker and current_content_lines:
        content = " ".join(current_content_lines).strip()
        if len(content) > 20:
            turns.append(
                SpeakerTurn(
                    speaker_name=current_speaker.strip(),
                    speaker_role=current_role,
                    content=content,
                    section_type=current_section,
                    turn_index=turn_index,
                )
            )

    return turns


def extract_quarter_year(text: str) -> tuple[str, int]:
    """
    Try to extract the quarter and fiscal year from transcript text.

    Looks for patterns like:
        - "Q3 2024"
        - "Third Quarter 2024"
        - "Fiscal Year 2024 First Quarter"
        - "FY2024 Q1"
    """
    quarter_map = {
        "first": "Q1", "1st": "Q1",
        "second": "Q2", "2nd": "Q2",
        "third": "Q3", "3rd": "Q3",
        "fourth": "Q4", "4th": "Q4",
    }

    # Pattern: Q1 2024, Q2 2025, etc.
    match = re.search(r"Q([1-4])\s*[\'\s]*(\d{4})", text, re.IGNORECASE)
    if match:
        return f"Q{match.group(1)}", int(match.group(2))

    # Pattern: "First Quarter 2024", "Third Quarter Fiscal 2025"
    for word, quarter in quarter_map.items():
        pattern = rf"{word}\s+quarter\s+(?:fiscal\s+)?(?:year\s+)?(\d{{4}})"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return quarter, int(match.group(1))

    # Pattern: "FY2024 Q1" or "FY24 Q3"
    match = re.search(r"FY\s*(\d{2,4})\s*Q([1-4])", text, re.IGNORECASE)
    if match:
        year_str = match.group(1)
        year = int(year_str) if len(year_str) == 4 else 2000 + int(year_str)
        return f"Q{match.group(2)}", year

    return "Q0", 0


def parse_transcript(
    html_content: str,
    company_name: str = "",
    quarter: str = "",
    year: int = 0,
) -> ParsedTranscript:
    """
    Parse a raw HTML earnings call transcript into structured data.

    This is the main entry point for transcript parsing. Takes raw
    HTML from an EDGAR filing and returns a ParsedTranscript with
    speaker turns, roles, and section labels.

    Args:
        html_content: Raw HTML content of the filing
        company_name: Company name (overrides auto-detection)
        quarter: Quarter label like "Q3" (overrides auto-detection)
        year: Fiscal year (overrides auto-detection)

    Returns:
        ParsedTranscript with speaker turns and metadata
    """
    # Stage 1: Clean HTML to plain text
    clean_text = clean_html(html_content)

    # Stage 2: Auto-detect quarter/year if not provided
    if not quarter or year == 0:
        detected_q, detected_y = extract_quarter_year(clean_text[:2000])
        quarter = quarter or detected_q
        year = year or detected_y

    # Stage 3: Extract speaker turns
    turns = extract_speaker_turns(clean_text)

    # Stage 4: Collect unique speakers
    speakers = list(dict.fromkeys(turn.speaker_name for turn in turns))

    logger.info(
        "Parsed transcript: company=%s, quarter=%s %d, speakers=%d, turns=%d",
        company_name, quarter, year, len(speakers), len(turns),
    )

    return ParsedTranscript(
        company_name=company_name,
        quarter=quarter,
        year=year,
        speakers=speakers,
        turns=turns,
        raw_text=clean_text,
    )


def parse_transcript_from_json(data: dict) -> ParsedTranscript:
    """
    Parse a transcript from pre-structured JSON data.

    Used for loading sample/seed transcripts that are already
    structured (not raw HTML). The JSON format is:

    {
        "company_name": "Apple Inc.",
        "ticker": "AAPL",
        "quarter": "Q3",
        "year": 2024,
        "turns": [
            {
                "speaker_name": "Tim Cook",
                "speaker_role": "ceo",
                "section_type": "prepared_remarks",
                "content": "..."
            }
        ]
    }

    Args:
        data: Dictionary with transcript data

    Returns:
        ParsedTranscript object
    """
    turns = []
    for i, turn_data in enumerate(data.get("turns", [])):
        turns.append(
            SpeakerTurn(
                speaker_name=turn_data["speaker_name"],
                speaker_role=turn_data.get("speaker_role", "unknown"),
                content=turn_data["content"],
                section_type=turn_data.get("section_type", "unknown"),
                turn_index=i,
            )
        )

    speakers = list(dict.fromkeys(t.speaker_name for t in turns))

    return ParsedTranscript(
        company_name=data.get("company_name", ""),
        quarter=data.get("quarter", ""),
        year=data.get("year", 0),
        speakers=speakers,
        turns=turns,
    )
