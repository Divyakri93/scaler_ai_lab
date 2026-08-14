import pytest
from pii_redactor.detectors.ner_detector import NERDetector
from pii_redactor.models import DocumentBlock, PIIType

def test_ner_detector_person():
    """
    Tests that PERSON labels are correctly mapped to FULL_NAME.
    """
    detector = NERDetector()
    block = DocumentBlock(
        block_id="b1",
        block_type="paragraph",
        text="Yesterday, Alice Smith met Bob Johnson to discuss the project.",
        element=None
    )
    entities = detector.detect(block)
    
    names = [e for e in entities if e.entity_type == PIIType.FULL_NAME]
    assert len(names) == 2
    
    texts = [n.original_text for n in names]
    assert "Alice Smith" in texts
    assert "Bob Johnson" in texts
    
    for n in names:
        assert n.confidence == 0.85
        assert n.source_detector == "spacy"
        assert n.metadata.get("spacy_label") == "PERSON"

def test_ner_detector_org():
    """
    Tests that ORG labels are correctly mapped to COMPANY_NAME.
    """
    detector = NERDetector()
    block = DocumentBlock(
        block_id="b2",
        block_type="paragraph",
        text="The agreement was signed by Microsoft Corp and Google LLC.",
        element=None
    )
    entities = detector.detect(block)
    
    orgs = [e for e in entities if e.entity_type == PIIType.COMPANY_NAME]
    assert len(orgs) == 2
    
    texts = [o.original_text for o in orgs]
    assert "Microsoft Corp" in texts
    assert "Google" in texts
    
    for o in orgs:
        assert o.confidence == 0.80
        assert o.source_detector == "spacy"
        assert o.metadata.get("spacy_label") == "ORG"

def test_ner_detector_gpe_ignored():
    """
    Tests that GPE (geopolitical) and LOC locations are NOT mapped to direct PII entities.
    """
    detector = NERDetector()
    block = DocumentBlock(
        block_id="b3",
        block_type="paragraph",
        text="He traveled from London, United Kingdom to Tokyo, Japan.",
        element=None
    )
    entities = detector.detect(block)
    # Ensure no entities are returned (since we don't map GPE/LOC to direct PII here)
    assert len(entities) == 0
