import logging
import re
from typing import Optional
from faker import Faker

from pii_redactor.models import PIIType

logger = logging.getLogger(__name__)

class FakerProvider:
    """
    Generates realistic, synthetic replacements using Faker.
    Supports seeds for deterministic, reproducible outputs.
    """

    def __init__(self, seed: Optional[int] = None) -> None:
        self.fake = Faker()
        if seed is not None:
            self.fake.seed_instance(seed)
            logger.info(f"Initialized Faker with seed {seed}")
        else:
            logger.info("Initialized Faker with random seed")

    def generate(self, entity_type: PIIType, original_text: str) -> str:
        """
        Generates a synthetic replacement based on the entity type and original text formatting.
        """
        if entity_type == PIIType.FULL_NAME:
            return self.fake.name()

        elif entity_type == PIIType.EMAIL:
            # Generate a realistic email prefix and suffix
            # Note: mapping engine will override local prefix if name is mapped
            return f"{self.fake.user_name()}@{self.fake.free_email_domain()}"

        elif entity_type == PIIType.PHONE:
            # Faker generates realistic phone numbers
            return self.fake.phone_number()

        elif entity_type == PIIType.COMPANY_NAME:
            return self.fake.company()

        elif entity_type == PIIType.ADDRESS:
            # Flatten multi-line address to fit contiguous DOCX text runs
            return self.fake.address().replace("\n", ", ")

        elif entity_type == PIIType.SSN:
            return self.fake.ssn()

        elif entity_type == PIIType.CREDIT_CARD:
            return self.fake.credit_card_number()

        elif entity_type == PIIType.IP_ADDRESS:
            # Check if original is IPv6
            if ":" in original_text:
                return self.fake.ipv6()
            return self.fake.ipv4()

        elif entity_type == PIIType.DATE_OF_BIRTH:
            # Generate date of birth for someone aged 18 to 90
            dob_dt = self.fake.date_of_birth(minimum_age=18, maximum_age=90)
            
            # Format date according to original separator
            if "-" in original_text:
                parts = original_text.split("-")
                if len(parts[0]) == 4:
                    return dob_dt.strftime("%Y-%m-%d")
                return dob_dt.strftime("%d-%m-%Y")
            elif "/" in original_text:
                parts = original_text.split("/")
                if len(parts[0]) == 4:
                    return dob_dt.strftime("%Y/%m/%d")
                return dob_dt.strftime("%d/%m/%Y")
            
            return dob_dt.strftime("%Y-%m-%d")

        else:
            # Fallback placeholder
            return f"[REDACTED_{entity_type.name}]"
