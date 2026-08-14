import pytest
from pii_redactor.replacement.replacement_engine import ReplacementEngine
from pii_redactor.models import PIIEntity, PIIType

def test_replacement_determinism():
    """
    Checks that same seed produces identical synthetic values.
    """
    # Create two engines with the same seed
    engine1 = ReplacementEngine(seed=42)
    engine2 = ReplacementEngine(seed=42)

    name_entity = PIIEntity(
        entity_type=PIIType.FULL_NAME,
        original_text="Alice Smith",
        start=0,
        end=11,
        confidence=1.0,
        source_detector="test"
    )

    r1 = engine1.get_replacement(name_entity)
    r2 = engine2.get_replacement(name_entity)

    assert r1 == r2  # Must be identical due to same seed

def test_replacement_consistency():
    """
    Checks that the same entity gets the same replacement every time.
    """
    engine = ReplacementEngine(seed=10)

    name_entity = PIIEntity(
        entity_type=PIIType.FULL_NAME,
        original_text="Alice Smith",
        start=0,
        end=11,
        confidence=1.0,
        source_detector="test"
    )

    r1 = engine.get_replacement(name_entity)
    # Fetch again
    r2 = engine.get_replacement(name_entity)
    
    assert r1 == r2
    
    # Case insensitivity lookup test
    name_entity_caps = PIIEntity(
        entity_type=PIIType.FULL_NAME,
        original_text="ALICE SMITH",
        start=0,
        end=11,
        confidence=1.0,
        source_detector="test"
    )
    r3 = engine.get_replacement(name_entity_caps)
    assert r1 == r3

def test_cross_entity_alignment():
    """
    Checks that name parts are aligned with email replacements.
    """
    engine = ReplacementEngine(seed=123)

    name_entity = PIIEntity(
        entity_type=PIIType.FULL_NAME,
        original_text="Rashi Patil",
        start=0,
        end=11,
        confidence=1.0,
        source_detector="test"
    )

    # Trigger name replacement (will seed name part mappings)
    name_rep = engine.get_replacement(name_entity)
    # Let's say name_rep is "John Doe" (or whatever Faker seeds)
    # Split name_rep into first and last
    first_fake, last_fake = name_rep.lower().split()

    email_entity = PIIEntity(
        entity_type=PIIType.EMAIL,
        original_text="rashi.patil@gmail.com",
        start=0,
        end=21,
        confidence=1.0,
        source_detector="test"
    )

    email_rep = engine.get_replacement(email_entity)
    
    # Expected: "first_fake.last_fake@example.com"
    expected_email = f"{first_fake}.{last_fake}@example.com"
    assert email_rep == expected_email

    # Check with different delimiter (e.g. underscore)
    email_entity_under = PIIEntity(
        entity_type=PIIType.EMAIL,
        original_text="rashi_patil@gmail.com",
        start=0,
        end=21,
        confidence=1.0,
        source_detector="test"
    )
    email_rep_under = engine.get_replacement(email_entity_under)
    expected_email_under = f"{first_fake}_{last_fake}@example.com"
    assert email_rep_under == expected_email_under
