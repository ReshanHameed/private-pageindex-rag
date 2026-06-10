"""Regex-based entity extraction for enriching deterministic summaries."""

import re

EMAIL_RE = re.compile(r"\b[\w\.-]+@[\w\.-]+\.\w{2,}\b")
# US and common phone formats (e.g. 555-555-5555, (555) 555-5555, +1 555...)
PHONE_RE = re.compile(r"(?:\b|\+)(?:\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
# Matches HTTP/HTTPS URLs and bare www. URLs
URL_RE = re.compile(r"\b(?:https?://|www\.)[^\s()<>]+(?:\([\w\d]+\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’])")

# Labels to match lines and extract names/entities
LABEL_RE = re.compile(
    r"\b(?:contacts|author|submitted\s+by|prepared\s+by|team\s+members?|prepared\s+for)\s*:?\s*(.+)",
    re.IGNORECASE
)


def extract_key_entities(text: str) -> list[str]:
    """Extract key entities (emails, phones, URLs, labeled names) from text.

    This runs during indexing to enrich the deterministic summaries of nodes,
    allowing downstream lexical and LLM search to easily find these details.
    """
    entities: list[str] = []

    # 1. Extract emails
    for email in EMAIL_RE.findall(text):
        if email not in entities:
            entities.append(email)

    # 2. Extract phone numbers
    for phone in PHONE_RE.findall(text):
        cleaned_phone = phone.strip()
        if cleaned_phone and cleaned_phone not in entities:
            entities.append(cleaned_phone)

    # 3. Extract URLs
    for url in URL_RE.findall(text):
        cleaned_url = url.strip()
        if cleaned_url and cleaned_url not in entities:
            entities.append(cleaned_url)

    # 4. Extract names/text following common labels (line-by-line check)
    for line in text.splitlines():
        match = LABEL_RE.search(line)
        if match:
            extracted_text = match.group(1).strip()
            # Clean up trailing punctuation
            extracted_text = re.sub(r"^[.:\s]+|[.:\s]+$", "", extracted_text)
            if extracted_text and len(extracted_text) < 120:
                # Split multiple names separated by comma, semicolon, or "and"
                parts = [p.strip() for p in re.split(r",|;| and ", extracted_text)]
                for part in parts:
                    part = re.sub(r"\s+", " ", part)
                    # Limit name/entity length to keep summaries concise (3 to 50 chars)
                    if 3 <= len(part) <= 50 and part not in entities:
                        entities.append(part)

    return entities
