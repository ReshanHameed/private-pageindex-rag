"""Unit tests for entity extraction helpers."""

from private_pageindex.indexing.entity_extraction import extract_key_entities


def test_extract_emails():
    text = "Please reach out to support@example.com or info.service@corp.co.uk for help."
    entities = extract_key_entities(text)
    assert "support@example.com" in entities
    assert "info.service@corp.co.uk" in entities


def test_extract_phone_numbers():
    text = "Call us at 555-123-4567 or international number +1-555-987-6543."
    entities = extract_key_entities(text)
    assert "555-123-4567" in entities
    assert "+1-555-987-6543" in entities or "555-987-6543" in entities


def test_extract_urls():
    text = "Visit https://example.com/docs or read https://www.wikipedia.org for details."
    entities = extract_key_entities(text)
    assert "https://example.com/docs" in entities
    assert "https://www.wikipedia.org" in entities


def test_extract_contacts_and_names():
    text = (
        "CONTACTS: David Jefferson, Carlos Gomez\n"
        "Author: Reshan Hameed H\n"
        "Submitted by: Bagathesh M.V and Aravinth Selva P\n"
        "Prepared by: Some Corporate Department"
    )
    entities = extract_key_entities(text)
    assert "David Jefferson" in entities
    assert "Carlos Gomez" in entities
    assert "Reshan Hameed H" in entities
    assert "Bagathesh M.V" in entities
    assert "Aravinth Selva P" in entities
    assert "Some Corporate Department" in entities


def test_extract_key_entities_deduplicates():
    text = "Email support@example.com or support@example.com again."
    entities = extract_key_entities(text)
    assert entities.count("support@example.com") == 1
