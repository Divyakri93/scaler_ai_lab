import logging
import re
from typing import List

from pii_redactor.detectors.base import BaseDetector
from pii_redactor.models import DocumentBlock, PIIEntity, PIIType

logger = logging.getLogger(__name__)

def luhn_checksum(card_number: str) -> bool:
    """
    Validates a credit card number using the Luhn (mod 10) algorithm.
    """
    # Remove any non-digits
    digits_str = re.sub(r"\D", "", card_number)
    if not digits_str or not digits_str.isdigit():
        return False
    
    try:
        digits = [int(c) for c in digits_str]
    except ValueError:
        return False

    # Perform Mod 10 checksum
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    checksum = sum(odd_digits)
    for d in even_digits:
        checksum += sum(divmod(d * 2, 10))
    return checksum % 10 == 0

class RegexDetector(BaseDetector):
    """
    Detects highly structured PII entities using regular expressions and validation logic.
    """

    def __init__(self) -> None:
        # 1. Email pattern (RFC 5322-compliant boundary)
        self.email_pattern = re.compile(
            r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"
        )

        # 2. Phone pattern: supports local 10 digits, +91-..., (123) 456-..., etc.
        self.phone_pattern = re.compile(
            r"(?<!\w)(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{4}\b"
        )

        # 3. SSN pattern: US format XXX-XX-XXXX
        self.ssn_pattern = re.compile(
            r"\b\d{3}-\d{2}-\d{4}\b"
        )

        # 4. IP Address: IPv4 (strictly 0-255 octets) and IPv6
        self.ipv4_pattern = re.compile(
            r"\b(?:(?:25[0-5]|2[0-4][0-9]|[0-1]?[0-9]{1,2})\.){3}(?:25[0-5]|2[0-4][0-9]|[0-1]?[0-9]{1,2})\b"
        )
        self.ipv6_pattern = re.compile(
            r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b"
        )

        # 5. Credit Card pattern: 13 to 19 digits separated by optional spaces/hyphens
        self.credit_card_pattern = re.compile(
            r"\b(?:\d[-\s]?){12,18}\d\b"
        )

        # 6. Generic Date pattern: YYYY-MM-DD, DD/MM/YYYY, MM/DD/YYYY, etc.
        self.date_pattern = re.compile(
            r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b|\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b"
        )

    def detect(self, block: DocumentBlock) -> List[PIIEntity]:
        """
        Runs regex rules on the document block text.
        """
        entities: List[PIIEntity] = []
        text = block.text

        if not text:
            return entities

        # 1. Detect Emails
        for match in self.email_pattern.finditer(text):
            entities.append(PIIEntity(
                entity_type=PIIType.EMAIL,
                original_text=match.group(),
                start=match.start(),
                end=match.end(),
                confidence=0.99,
                source_detector="regex"
            ))

        # 2. Detect SSNs
        for match in self.ssn_pattern.finditer(text):
            entities.append(PIIEntity(
                entity_type=PIIType.SSN,
                original_text=match.group(),
                start=match.start(),
                end=match.end(),
                confidence=0.99,
                source_detector="regex"
            ))

        # 3. Detect IP Addresses (IPv4 and IPv6)
        for match in self.ipv4_pattern.finditer(text):
            entities.append(PIIEntity(
                entity_type=PIIType.IP_ADDRESS,
                original_text=match.group(),
                start=match.start(),
                end=match.end(),
                confidence=0.99,
                source_detector="regex"
            ))
        for match in self.ipv6_pattern.finditer(text):
            entities.append(PIIEntity(
                entity_type=PIIType.IP_ADDRESS,
                original_text=match.group(),
                start=match.start(),
                end=match.end(),
                confidence=0.99,
                source_detector="regex"
            ))

        # 4. Detect Credit Cards (validated with Luhn checksum)
        for match in self.credit_card_pattern.finditer(text):
            raw_match = match.group()
            # Clean non-digits
            cleaned = re.sub(r"\D", "", raw_match)
            # Standard length of credit cards is 13 to 19 digits
            if 13 <= len(cleaned) <= 19 and luhn_checksum(cleaned):
                entities.append(PIIEntity(
                    entity_type=PIIType.CREDIT_CARD,
                    original_text=raw_match,
                    start=match.start(),
                    end=match.end(),
                    confidence=0.99,
                    source_detector="regex"
                ))

        # 5. Detect Phone Numbers
        # Note: phone numbers can overlap with credit cards or SSNs.
        # We collect them here; our conflict resolver handles overlaps later.
        for match in self.phone_pattern.finditer(text):
            raw_match = match.group()
            # Basic validation: ensure it contains at least 7 digits to prevent matching small numbers
            digits_count = len(re.sub(r"\D", "", raw_match))
            if 7 <= digits_count <= 15:
                entities.append(PIIEntity(
                    entity_type=PIIType.PHONE,
                    original_text=raw_match,
                    start=match.start(),
                    end=match.end(),
                    confidence=0.95,
                    source_detector="regex"
                ))

        # 6. Detect Dates
        # Date is captured as a generic date first; contextual rules promote it to DATE_OF_BIRTH
        for match in self.date_pattern.finditer(text):
            entities.append(PIIEntity(
                # Use DATE_OF_BIRTH temporarily or keep as generic DATE?
                # We can store a temporary field in metadata indicating it's a generic date
                entity_type=PIIType.DATE_OF_BIRTH,
                original_text=match.group(),
                start=match.start(),
                end=match.end(),
                confidence=0.50,  # Low confidence, needs context promotion
                source_detector="regex",
                metadata={"is_generic_date": True}
            ))

        return entities
