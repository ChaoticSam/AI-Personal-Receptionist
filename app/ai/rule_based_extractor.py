"""
Rule-Based Slot Extractor — fast regex/heuristic extraction layer.

Handles the majority of simple customer inputs in < 5ms without any LLM call.
Supports English and Hinglish (Hindi + English mixed) inputs.

Extracted slots:
  - quantity      → integer   ("two", "2", "do", "teen")
  - deadline      → ISO date  ("tomorrow", "kal", "next Monday")
  - customer_notes → string   (delivery-related phrases)
  - custom_fields → dict      (text content after "write"/"print"/"likhna")

Does NOT extract:
  - product_name  → always delegated to LLM (requires catalog context)
"""

import re
from datetime import datetime


# ---------------------------------------------------------------------------
# Quantity extraction
# ---------------------------------------------------------------------------

# English word → integer
_WORD_TO_NUM = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "fifteen": 15, "twenty": 20,
    "thirty": 30, "forty": 40, "fifty": 50, "hundred": 100,
    # Hindi / Hinglish numbers
    "ek": 1, "do": 2, "teen": 3, "char": 4, "paanch": 5,
    "chhe": 6, "saat": 7, "aath": 8, "nau": 9, "das": 10,
}

# Regex: digit(s) optionally followed by "piece/pcs/unit/nos"
_DIGIT_QTY_RE = re.compile(
    r"\b(\d+)\s*(?:piece|pieces|pcs|units?|nos?|mugs?|cups?|items?)?\b",
    re.IGNORECASE,
)

# Correction phrases — "actually X", "make it X", "change to X", "instead X"
_CORRECTION_RE = re.compile(
    r"(?:actually|make\s+it|change\s+to|instead\s+(?:of\s+)?(?:that\s+)?(?:make\s+it\s+)?)\s*(\d+|\w+)",
    re.IGNORECASE,
)


def _extract_quantity(text: str) -> int | None:
    # 1. Correction phrases take priority (latest override semantics)
    m = _CORRECTION_RE.search(text)
    if m:
        val = m.group(1).lower()
        if val.isdigit():
            return int(val)
        if val in _WORD_TO_NUM:
            return _WORD_TO_NUM[val]

    # 2. Digit directly in text
    m = _DIGIT_QTY_RE.search(text)
    if m:
        n = int(m.group(1))
        # Guard: quantities > 999 are almost certainly not order quantities
        if 1 <= n <= 999:
            return n

    # 3. Word number
    lower = text.lower()
    for word, num in _WORD_TO_NUM.items():
        if re.search(rf"\b{word}\b", lower):
            return num

    return None


# ---------------------------------------------------------------------------
# Deadline extraction  (English + Hinglish)
# ---------------------------------------------------------------------------

# Hinglish → English normalization map
_HINGLISH_DATE_MAP = {
    "kal": "tomorrow",
    "parso": "day after tomorrow",
    "aaj": "today",
    "agli week": "next week",
    "agla week": "next week",
    "agli somwar": "next monday",
    "agli mangalwar": "next tuesday",
    "agli budhwar": "next wednesday",
    "agli guruwar": "next thursday",
    "agli shukrawar": "next friday",
}

# "by X", "tak X", "before X", "within X days"
_DEADLINE_KEYWORDS_RE = re.compile(
    r"(?:by|before|until|tak|within|deliver\s+by|chahiye\s+by)\s+(.+?)(?:\s+(?:and|,)|$)",
    re.IGNORECASE,
)


def _normalize_hinglish_date(text: str) -> str:
    """Replace Hinglish date terms with English equivalents before parsing."""
    lower = text.lower()
    for hinglish, english in _HINGLISH_DATE_MAP.items():
        lower = lower.replace(hinglish, english)
    # Strip Hinglish + common remainder words that confuse dateparser
    for filler in ("tak", "chahiye", "se pehle", "ke baad", "mujhe", "please", "jaldi",
                   "deliver", "karo", "karna", "hai", "do", "dena"):
        lower = re.sub(rf"\b{filler}\b", "", lower).strip()
    # Collapse multiple spaces
    lower = re.sub(r"\s+", " ", lower).strip()
    return lower


_WEEKDAY_MAP = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
    # Hindi weekday names
    "somwar": 0, "mangalwar": 1, "budhwar": 2, "guruwar": 3,
    "shukrawar": 4, "shaniwar": 5, "raviwar": 6,
}

_NEXT_WEEKDAY_RE = re.compile(
    r"(?:next|agli)\s+(" + "|".join(_WEEKDAY_MAP.keys()) + r")\b",
    re.IGNORECASE,
)


def _next_weekday_date(weekday_name: str) -> str:
    """Return the ISO date of the next occurrence of the given weekday."""
    from datetime import timedelta
    target = _WEEKDAY_MAP[weekday_name.lower()]
    today = datetime.utcnow().date()
    days_ahead = (target - today.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7  # "next Monday" when today is Monday → 7 days forward
    return (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")


def _extract_deadline(text: str) -> str | None:
    """Return ISO 8601 date string (YYYY-MM-DD) or None."""
    try:
        # 1. Explicit "next <weekday>" pattern (dateparser can't handle this)
        m = _NEXT_WEEKDAY_RE.search(text)
        if m:
            return _next_weekday_date(m.group(1))

        import dateparser

        normalized = _normalize_hinglish_date(text)

        # 2. Try extracting from deadline keyword phrases first
        m = _DEADLINE_KEYWORDS_RE.search(normalized)
        candidate = m.group(1).strip() if m else normalized

        parsed = dateparser.parse(
            candidate,
            settings={
                "PREFER_DATES_FROM": "future",
                "RETURN_AS_TIMEZONE_AWARE": False,
                "PREFER_DAY_OF_MONTH": "first",
            },
        )
        if parsed and parsed.date() >= datetime.utcnow().date():
            return parsed.strftime("%Y-%m-%d")
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Text / custom_fields extraction
# ---------------------------------------------------------------------------

# Keywords that signal the customer is dictating content to print/write
_TEXT_TRIGGER_RE = re.compile(
    r"(?:write|print|engrave|add|put|type|inscribe|likhna|likho|likhe|text|saying)\s+[\"']?(.+?)[\"']?"
    r"(?:\s+(?:on\s+it|on\s+the|onto|upon|there))?$",
    re.IGNORECASE,
)

# "on it write X", "with text X", "text: X"
_TEXT_ALT_RE = re.compile(
    r"""(?:with\s+(?:text|message)|text\s*[:=]|message\s*[:=])\s*[\"']?(.+?)[\"']?$""",
    re.IGNORECASE,
)


def _extract_text_content(text: str) -> str | None:
    m = _TEXT_TRIGGER_RE.search(text)
    if m:
        return m.group(1).strip().strip("\"'")
    m = _TEXT_ALT_RE.search(text)
    if m:
        return m.group(1).strip().strip("\"'")
    return None


# ---------------------------------------------------------------------------
# Notes extraction  (delivery / special instructions)
# ---------------------------------------------------------------------------

_NOTES_PATTERNS = [
    re.compile(r"(?:urgent|urgently|asap|as\s+soon\s+as\s+possible)", re.IGNORECASE),
    re.compile(r"(?:gift\s+wrap|gift\s+wrapped|wrapped\s+nicely)", re.IGNORECASE),
    re.compile(r"(?:fragile|handle\s+with\s+care)", re.IGNORECASE),
    re.compile(r"(?:special\s+(?:instruction|request)[s]?[:\s]+)(.+)", re.IGNORECASE),
]

def _extract_notes(text: str) -> str | None:
    for pattern in _NOTES_PATTERNS:
        m = pattern.search(text)
        if m:
            # If the pattern has a capture group, return it; else return the full match
            return m.group(1).strip() if m.lastindex else m.group(0).strip()
    return None


# ---------------------------------------------------------------------------
# Context-aware extraction for known expected slot
# ---------------------------------------------------------------------------

def _context_aware_extract(text: str, expected_slot: str) -> dict:
    """
    When the AI just asked for a specific slot (e.g. "What text should be printed?"),
    interpret the entire customer reply as that slot's value — no keyword matching needed.
    Avoids mis-classifying "Best Dad Ever" as a product name.
    """
    result: dict = {}
    stripped = text.strip().strip("\"'")

    if expected_slot == "quantity":
        qty = _extract_quantity(text)
        if qty:
            result["quantity"] = qty
        # If still not found, maybe they just said a number word
        elif stripped.isdigit():
            result["quantity"] = int(stripped)

    elif expected_slot in ("text", "message", "content"):
        result["custom_fields"] = {expected_slot: stripped}

    elif expected_slot == "deadline":
        d = _extract_deadline(text)
        if d:
            result["deadline"] = d
        else:
            # Store raw as customer_notes if date parsing fails
            result["customer_notes"] = stripped

    else:
        # Generic custom field (image description, size, colour, etc.)
        result["custom_fields"] = {expected_slot: stripped}

    return result


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def rule_extract(
    text: str,
    required_custom_fields: list[str] | None = None,
    expected_slot: str | None = None,
) -> dict:
    """
    Fast rule-based slot extraction. Returns a partial slots dict.
    Only includes keys where something was actually found (no None padding).

    Args:
        text: Raw customer message.
        required_custom_fields: Product-specific fields (e.g. ["text", "image"]).
        expected_slot: The slot the AI most recently asked about (context-aware mode).

    Returns:
        Partial dict with any of: quantity, deadline, customer_notes, custom_fields
        Plus metadata: rule_extracted=True, tokens_used=0
    """
    required_custom_fields = required_custom_fields or []
    slots: dict = {}

    # Context-aware mode: AI just asked for a specific slot
    if expected_slot:
        ctx = _context_aware_extract(text, expected_slot)
        if ctx:
            slots.update(ctx)
            slots["rule_extracted"] = True
            slots["tokens_used"] = 0
            return slots

    # --- Standard extraction ---

    qty = _extract_quantity(text)
    if qty is not None:
        slots["quantity"] = qty

    deadline = _extract_deadline(text)
    if deadline:
        slots["deadline"] = deadline

    notes = _extract_notes(text)
    if notes:
        slots["customer_notes"] = notes

    # Extract text content for known custom fields
    text_content = _extract_text_content(text)
    if text_content:
        # Map to the first text-like custom field if any, else use generic "text"
        text_fields = [f for f in required_custom_fields if f in ("text", "message", "content")]
        target_field = text_fields[0] if text_fields else "text"
        slots.setdefault("custom_fields", {})[target_field] = text_content

    slots["rule_extracted"] = bool(slots)
    slots["tokens_used"] = 0
    return slots
