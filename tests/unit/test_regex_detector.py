import pytest
from pii_redactor.detectors.regex_detector import RegexDetector, luhn_checksum
from pii_redactor.models import DocumentBlock, PIIType

def test_luhn_checksum():
    """
    Verifies the Luhn algorithm with valid and invalid credit card numbers.
    """
    # Valid Visa card (standard test card)
    assert luhn_checksum("4111 1111 1111 1111") is True
    assert luhn_checksum("4111-1111-1111-1111") is True
    assert luhn_checksum("4111111111111111") is True
    
    # Invalid card number (checksum fails)
    assert luhn_checksum("4111111111111112") is False
    # Non-numeric
    assert luhn_checksum("abcd") is False
    # Empty
    assert luhn_checksum("") is False

def test_regex_detector_emails():
    """
    Tests Email detection patterns.
    """
    detector = RegexDetector()
    
    # 1. Body containing multiple emails
    block = DocumentBlock(
        block_id="b1",
        block_type="paragraph",
        text="Please contact rashi.patil@gmail.com or test-user+1@domain.co.in for info.",
        element=None
    )
    entities = detector.detect(block)
    emails = [e for e in entities if e.entity_type == PIIType.EMAIL]
    
    assert len(emails) == 2
    assert emails[0].original_text == "rashi.patil@gmail.com"
    assert emails[0].start == 15
    assert emails[0].end == 36
    
    assert emails[1].original_text == "test-user+1@domain.co.in"
    assert emails[1].start == 40
    assert emails[1].end == 64

def test_regex_detector_ssn():
    """
    Tests SSN detection patterns.
    """
    detector = RegexDetector()
    block = DocumentBlock(
        block_id="b2",
        block_type="paragraph",
        text="My SSN is 123-45-6789, which is a secret.",
        element=None
    )
    entities = detector.detect(block)
    ssns = [e for e in entities if e.entity_type == PIIType.SSN]
    
    assert len(ssns) == 1
    assert ssns[0].original_text == "123-45-6789"
    assert ssns[0].start == 10
    assert ssns[0].end == 21

def test_regex_detector_ips():
    """
    Tests IPv4 and IPv6 detection and bounds.
    """
    detector = RegexDetector()
    block = DocumentBlock(
        block_id="b3",
        block_type="paragraph",
        text="Connect to IPv4 192.168.1.254 and IPv6 2001:db8:0:0:0:0:0:1. Don't connect to 300.400.500.600.",
        element=None
    )
    entities = detector.detect(block)
    ips = [e for e in entities if e.entity_type == PIIType.IP_ADDRESS]
    
    assert len(ips) == 2
    assert "192.168.1.254" in [e.original_text for e in ips]
    assert "2001:db8:0:0:0:0:0:1" in [e.original_text for e in ips]
    # Check that invalid IP 300.400.500.600 is NOT matched
    assert "300.400.500.600" not in [e.original_text for e in ips]

def test_regex_detector_credit_cards():
    """
    Tests credit card numbers and verifies Luhn is integrated correctly.
    """
    detector = RegexDetector()
    block = DocumentBlock(
        block_id="b4",
        block_type="paragraph",
        text="Valid CC: 4111-1111-1111-1111. Invalid CC: 4111-1111-1111-1112. Order ID: 1234567890123456.",
        element=None
    )
    entities = detector.detect(block)
    ccs = [e for e in entities if e.entity_type == PIIType.CREDIT_CARD]
    
    assert len(ccs) == 1
    assert ccs[0].original_text == "4111-1111-1111-1111"
    # Ensure invalid CC (4111-1111-1111-1112) is NOT matched
    assert "4111-1111-1111-1112" not in [e.original_text for e in ccs]
    # Ensure standard order ID is NOT matched (Luhn checksum fails)
    assert "1234567890123456" not in [e.original_text for e in ccs]

def test_regex_detector_phones():
    """
    Tests various phone number structures.
    """
    detector = RegexDetector()
    block = DocumentBlock(
        block_id="b5",
        block_type="paragraph",
        text="Call +91 9876543210, +91-9876543210, 9876543210 or US number (123) 456-7890. Do not match Ticket 123456.",
        element=None
    )
    entities = detector.detect(block)
    phones = [e for e in entities if e.entity_type == PIIType.PHONE]
    
    assert len(phones) == 4
    texts = [p.original_text for p in phones]
    assert "+91 9876543210" in texts
    assert "+91-9876543210" in texts
    assert "9876543210" in texts
    assert "(123) 456-7890" in texts
    # Ensure small numbers/ticket IDs are not matched
    assert "123456" not in texts

def test_regex_detector_dates():
    """
    Tests generic date format matching.
    """
    detector = RegexDetector()
    block = DocumentBlock(
        block_id="b6",
        block_type="paragraph",
        text="Birth date is 12/04/1999 and another date is 2026-08-14.",
        element=None
    )
    entities = detector.detect(block)
    dates = [e for e in entities if e.entity_type == PIIType.DATE_OF_BIRTH]
    
    assert len(dates) == 2
    texts = [d.original_text for d in dates]
    assert "12/04/1999" in texts
    assert "2026-08-14" in texts
    
    # Assert they are marked as generic dates in metadata
    for d in dates:
        assert d.metadata.get("is_generic_date") is True
        assert d.confidence == 0.50
