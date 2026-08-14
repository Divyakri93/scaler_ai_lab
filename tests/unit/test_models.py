import pytest
from pydantic import ValidationError
from pii_redactor.models import PIIEntity, PIIType
from pii_redactor.config import RedactorConfig

def test_pii_entity_validation_success():
    """
    Ensures a valid PIIEntity passes all validation rules.
    """
    entity = PIIEntity(
        entity_type=PIIType.EMAIL,
        original_text="test@example.com",
        start=5,
        end=21,
        confidence=0.99,
        source_detector="regex"
    )
    assert entity.entity_type == PIIType.EMAIL
    assert entity.original_text == "test@example.com"
    assert entity.start == 5
    assert entity.end == 21
    assert entity.confidence == 0.99
    assert entity.source_detector == "regex"

def test_pii_entity_validation_failure_indices():
    """
    Ensures that start >= end throws a ValidationError.
    """
    with pytest.raises(ValidationError) as exc_info:
        PIIEntity(
            entity_type=PIIType.FULL_NAME,
            original_text="John",
            start=10,
            end=5,  # Invalid: end is less than start
            confidence=0.8,
            source_detector="spacy"
        )
    assert "Start index (10) must be less than end index (5)" in str(exc_info.value)

def test_pii_entity_validation_failure_length_mismatch():
    """
    Ensures that original_text length must match end - start.
    """
    with pytest.raises(ValidationError) as exc_info:
        PIIEntity(
            entity_type=PIIType.FULL_NAME,
            original_text="John",  # Length 4
            start=0,
            end=10,  # Expected length 10
            confidence=0.8,
            source_detector="spacy"
        )
    assert "Original text length (4) does not match span length (10)" in str(exc_info.value)

def test_pii_entity_validation_failure_confidence_bounds():
    """
    Ensures confidence scores outside [0.0, 1.0] throw an error.
    """
    with pytest.raises(ValidationError) as exc_info:
        PIIEntity(
            entity_type=PIIType.IP_ADDRESS,
            original_text="127.0.0.1",
            start=0,
            end=9,
            confidence=-0.1,  # Invalid confidence
            source_detector="regex"
        )
    assert "Input should be greater than or equal to 0" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info:
        PIIEntity(
            entity_type=PIIType.IP_ADDRESS,
            original_text="127.0.0.1",
            start=0,
            end=9,
            confidence=1.5,  # Invalid confidence
            source_detector="regex"
        )
    assert "Input should be less than or equal to 1" in str(exc_info.value)

def test_redactor_config_defaults():
    """
    Ensures configurations load correct defaults and fallbacks.
    """
    config = RedactorConfig()
    # Check overall default threshold
    assert config.overall_threshold == 0.70
    # Check specific defaults
    assert config.get_threshold(PIIType.EMAIL) == 0.95
    assert config.get_threshold(PIIType.ADDRESS) == 0.70
    # Check fallback behavior for a type not in thresholds mapping
    # (By default all types are in thresholds, but if we override it, it should fall back)
    config_custom = RedactorConfig(thresholds={PIIType.EMAIL: 0.90})
    assert config_custom.get_threshold(PIIType.EMAIL) == 0.90
    assert config_custom.get_threshold(PIIType.FULL_NAME) == 0.70  # Fallback to overall_threshold
