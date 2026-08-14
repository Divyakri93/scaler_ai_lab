from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from docx.text.run import Run
from pydantic import BaseModel, Field, model_validator, field_validator

class PIIType(str, Enum):
    """Supported PII entity categories."""
    FULL_NAME = "FULL_NAME"
    EMAIL = "EMAIL"
    PHONE = "PHONE"
    COMPANY_NAME = "COMPANY_NAME"
    ADDRESS = "ADDRESS"
    SSN = "SSN"
    CREDIT_CARD = "CREDIT_CARD"
    DATE_OF_BIRTH = "DATE_OF_BIRTH"
    IP_ADDRESS = "IP_ADDRESS"

class PIIEntity(BaseModel):
    """
    Validates and models a detected PII entity.
    """
    entity_type: PIIType
    original_text: str = Field(min_length=1)
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    confidence: float = Field(ge=0.0, le=1.0)
    source_detector: str = Field(min_length=1)
    normalized_value: Optional[str] = None
    replacement: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return v

    @model_validator(mode="after")
    def validate_indices(self) -> "PIIEntity":
        if self.start >= self.end:
            raise ValueError(f"Start index ({self.start}) must be less than end index ({self.end})")
        
        # Verify that original_text length matches the span length
        expected_len = self.end - self.start
        actual_len = len(self.original_text)
        if expected_len != actual_len:
            raise ValueError(
                f"Original text length ({actual_len}) does not match span length ({expected_len})"
            )
        return self

@dataclass
class RunInfo:
    run: Run
    text: str
    start: int                  # Start offset of the run's text in the unified block text
    end: int                    # End offset of the run's text in the unified block text

@dataclass
class DocumentBlock:
    block_id: str               # Unique identifier for the block
    block_type: str             # "paragraph", "table_cell", "header", "footer"
    text: str                   # Unified text content of the block
    element: Any                # Reference to python-docx Paragraph or TableCell object
    runs: List[RunInfo] = field(default_factory=list)
