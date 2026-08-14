import pytest
from pii_redactor.detectors.aggregator import DetectionAggregator
from pii_redactor.models import DocumentBlock, PIIEntity, PIIType

def test_conflict_resolution_priorities():
    """
    Checks that higher confidence overrides lower confidence on overlap.
    """
    aggregator = DetectionAggregator(detectors=[])

    # Overlapping candidates:
    # 1. Email (Regex) - starts at 10, ends at 31, confidence 0.99
    # 2. Full Name (spaCy) - starts at 10, ends at 21, confidence 0.85
    c1 = PIIEntity(
        entity_type=PIIType.EMAIL,
        original_text="alice.smith@gmail.com",
        start=10,
        end=31,
        confidence=0.99,
        source_detector="regex"
    )
    c2 = PIIEntity(
        entity_type=PIIType.FULL_NAME,
        original_text="alice.smith",
        start=10,
        end=21,
        confidence=0.85,
        source_detector="spacy"
    )

    resolved = aggregator.resolve_conflicts([c1, c2])
    # The higher confidence (Email at 0.99) must override the lower one
    assert len(resolved) == 1
    assert resolved[0].entity_type == PIIType.EMAIL
    assert resolved[0].original_text == "alice.smith@gmail.com"

def test_conflict_resolution_tiebreakers():
    """
    Checks that longer span wins when confidences are equal.
    """
    aggregator = DetectionAggregator(detectors=[])

    # Confidences are tied (0.95), but span lengths differ:
    # 1. Phone full match: 123-456-7890 (length 12)
    # 2. Phone partial match: 123-456 (length 7)
    c1 = PIIEntity(
        entity_type=PIIType.PHONE,
        original_text="123-456-7890",
        start=0,
        end=12,
        confidence=0.95,
        source_detector="regex"
    )
    c2 = PIIEntity(
        entity_type=PIIType.PHONE,
        original_text="123-456",
        start=0,
        end=7,
        confidence=0.95,
        source_detector="regex"
    )

    resolved = aggregator.resolve_conflicts([c1, c2])
    assert len(resolved) == 1
    assert resolved[0].original_text == "123-456-7890"

def test_detection_aggregator_full():
    """
    Verifies that all three detectors run and merge their entities correctly.
    """
    aggregator = DetectionAggregator()
    # Complex block with multiple types:
    # - Name (PERSON via spaCy)
    # - Email (Regex)
    # - Address (Contextual)
    block = DocumentBlock(
        block_id="b1",
        block_type="paragraph",
        text="Contact Alice Smith (alice.smith@gmail.com) at our office at 123 MG Road, Delhi.",
        element=None
    )
    
    entities = aggregator.detect(block)
    
    types = [e.entity_type for e in entities]
    assert PIIType.FULL_NAME in types
    assert PIIType.EMAIL in types
    assert PIIType.ADDRESS in types
    
    # Ensure they are in text order (ascending start offset)
    assert entities[0].entity_type == PIIType.FULL_NAME
    assert entities[0].original_text == "Alice Smith"
    
    assert entities[1].entity_type == PIIType.EMAIL
    assert entities[1].original_text == "alice.smith@gmail.com"
    
    assert entities[2].entity_type == PIIType.ADDRESS
    assert entities[2].original_text == "123 MG Road, Delhi"
