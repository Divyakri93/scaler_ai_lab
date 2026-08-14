import os
from typing import Dict, Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from pii_redactor.models import PIIType

class RedactorConfig(BaseSettings):
    """
    Application settings and configurations.
    Can be loaded from environment variables (prefixed with PII_)
    or custom configuration dicts.
    """
    model_config = SettingsConfigDict(
        env_prefix="PII_",
        case_sensitive=False,
        extra="ignore"
    )

    seed: Optional[int] = Field(
        default=None,
        description="Seed for Faker random generator to ensure reproducible synthetic values."
    )
    
    overall_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Overall confidence cutoff. Detections below this score are ignored."
    )

    # Individual confidence thresholds for PII categories
    thresholds: Dict[PIIType, float] = Field(
        default_factory=lambda: {
            PIIType.FULL_NAME: 0.80,
            PIIType.EMAIL: 0.95,
            PIIType.PHONE: 0.85,
            PIIType.COMPANY_NAME: 0.80,
            PIIType.ADDRESS: 0.70,
            PIIType.SSN: 0.95,
            PIIType.CREDIT_CARD: 0.95,
            PIIType.DATE_OF_BIRTH: 0.85,
            PIIType.IP_ADDRESS: 0.95,
        },
        description="Per-PII type confidence thresholds."
    )

    verbose: bool = Field(
        default=False,
        description="Whether to log detailed debug information."
    )

    def get_threshold(self, entity_type: PIIType) -> float:
        """
        Returns the specific threshold for the given PIIType,
        falling back to the overall_threshold if not explicitly defined.
        """
        return self.thresholds.get(entity_type, self.overall_threshold)
