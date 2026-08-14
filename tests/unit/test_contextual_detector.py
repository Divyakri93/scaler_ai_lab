import pytest
from pii_redactor.detectors.contextual_detector import ContextualDetector
from pii_redactor.models import DocumentBlock, PIIType

def test_contextual_dob_promotion():
    """
    Tests that a date is only promoted to DATE_OF_BIRTH when birth keywords are present.
    """
    detector = ContextualDetector()

    # Case 1: Positive match (birth keyword in lookback window)
    block_pos = DocumentBlock(
        block_id="b1",
        block_type="paragraph",
        text="Applicant's Date of Birth: 12/04/1999 is recorded.",
        element=None
    )
    entities_pos = detector.detect(block_pos)
    dobs_pos = [e for e in entities_pos if e.entity_type == PIIType.DATE_OF_BIRTH]
    
    assert len(dobs_pos) == 1
    assert dobs_pos[0].original_text == "12/04/1999"
    assert dobs_pos[0].confidence == 0.90
    assert dobs_pos[0].source_detector == "contextual_dob"

    # Case 2: Negative match (date is an invoice date, should be ignored)
    block_neg = DocumentBlock(
        block_id="b2",
        block_type="paragraph",
        text="Invoice Date: 12/04/1999. Please pay immediately.",
        element=None
    )
    entities_neg = detector.detect(block_neg)
    dobs_neg = [e for e in entities_neg if e.entity_type == PIIType.DATE_OF_BIRTH]
    
    assert len(dobs_neg) == 0

def test_contextual_addresses():
    """
    Tests address heuristic parsing and merging.
    """
    detector = ContextualDetector()

    # Case 1: Standard street suffix address (Pattern A)
    block_a = DocumentBlock(
        block_id="b3",
        block_type="paragraph",
        text="Our office is located at 123 MG Road, Delhi.",
        element=None
    )
    entities_a = detector.detect(block_a)
    addrs_a = [e for e in entities_a if e.entity_type == PIIType.ADDRESS]
    assert len(addrs_a) == 1
    assert addrs_a[0].original_text == "123 MG Road, Delhi"
    assert addrs_a[0].confidence == 0.75

    # Case 2: Flat / Sector block address (Pattern B)
    block_b = DocumentBlock(
        block_id="b4",
        block_type="paragraph",
        text="He lives at Flat 201, Tower B, Sector 62, Noida.",
        element=None
    )
    entities_b = detector.detect(block_b)
    addrs_b = [e for e in entities_b if e.entity_type == PIIType.ADDRESS]
    assert len(addrs_b) == 1
    assert addrs_b[0].original_text == "Flat 201, Tower B, Sector 62, Noida"

    # Case 3: Postal code proximity heuristic
    block_c = DocumentBlock(
        block_id="b5",
        block_type="paragraph",
        text="Please ship the package to House 45, Sector 4, Noida 201301.",
        element=None
    )
    entities_c = detector.detect(block_c)
    addrs_c = [e for e in entities_c if e.entity_type == PIIType.ADDRESS]
    assert len(addrs_c) == 1
    assert addrs_c[0].original_text == "House 45, Sector 4, Noida 201301"

    # Case 4: Negative case (no address details, just standard numbers)
    block_d = DocumentBlock(
        block_id="b6",
        block_type="paragraph",
        text="We processed 123456 records and generated 98765 invoices.",
        element=None
    )
    entities_d = detector.detect(block_d)
    addrs_d = [e for e in entities_d if e.entity_type == PIIType.ADDRESS]
    assert len(addrs_d) == 0
