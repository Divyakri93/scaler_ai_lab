import logging
import re
from typing import List

from pii_redactor.detectors.base import BaseDetector
from pii_redactor.models import DocumentBlock, PIIEntity, PIIType

logger = logging.getLogger(__name__)

class ContextualDetector(BaseDetector):
    """
    Detects context-sensitive PII categories:
    1. DATE_OF_BIRTH: Promotes date matches ONLY when birth keywords are nearby.
    2. ADDRESS: Identifies mailing addresses via street, unit, and postal heuristics.
    """

    def __init__(self) -> None:
        # Date regex: YYYY-MM-DD, DD/MM/YYYY, etc.
        self.date_pattern = re.compile(
            r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b|\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b"
        )
        self.birth_keywords = ["birth", "dob", "born", "birthdate", "d.o.b."]

        # Pattern A: House/plot number + street words + street suffix (case-insensitive)
        self.address_pattern_a = re.compile(
            r"\b\d+[-/a-zA-Z0-9]*\s+(?:[a-zA-Z0-9_]+\s+){1,4}"
            r"(?:Street|St|Road|Rd|Avenue|Ave|Drive|Dr|Lane|Ln|Sector|Flat|Tower|Apartment|Apt|Building|Bldg|Court|Ct|Circle|Cir)\b"
            r"(?:,\s+[a-zA-Z\s]+){0,3}"
            r"(?:,\s+\b\d{5}(?:-\d{4})?\b|,\s+\b\d{6}\b)?",
            re.IGNORECASE
        )

        # Pattern B: Unit descriptors + details + city + state + optional zip
        self.address_pattern_b = re.compile(
            r"\b(?:Flat|Apt|Apartment|Suite|Sector|Tower|Building|Bldg|Block|House|No)\s+[a-zA-Z0-9_#-]+"
            r"(?:,\s+[a-zA-Z0-9_#-]+)*,\s+[a-zA-Z\s]+"
            r"(?:,\s+\b\d{5}(?:-\d{4})?\b|,\s+\b\d{6}\b)?",
            re.IGNORECASE
        )

        # Postal codes: US ZIP or India Pincode
        self.postal_code_pattern = re.compile(
            r"\b\d{5}(?:-\d{4})?\b|\b\d{6}\b"
        )
        
        self.address_indicators = [
            "street", "st", "road", "rd", "avenue", "ave", "drive", "dr", "lane", "ln",
            "sector", "flat", "tower", "apartment", "apt", "building", "bldg", "house", "block"
        ]
        # Compile a pattern of address indicator words with word boundaries to prevent substring matching
        self.indicator_pattern = re.compile(
            r"\b(" + "|".join(self.address_indicators) + r")\b",
            re.IGNORECASE
        )

    def detect(self, block: DocumentBlock) -> List[PIIEntity]:
        entities: List[PIIEntity] = []
        text = block.text

        if not text or not text.strip():
            return entities

        # 1. Date of Birth Detection (Context Promoted)
        for match in self.date_pattern.finditer(text):
            start = match.start()
            end = match.end()
            date_str = match.group()

            # Scan up to 30 characters lookback window
            lookback_start = max(0, start - 30)
            context_window = text[lookback_start:start].lower()

            if any(kw in context_window for kw in self.birth_keywords):
                entities.append(PIIEntity(
                    entity_type=PIIType.DATE_OF_BIRTH,
                    original_text=date_str,
                    start=start,
                    end=end,
                    confidence=0.90,
                    source_detector="contextual_dob"
                ))

        # 2. Address Detection (Heuristic Spans)
        raw_spans = []

        # Try Pattern A matches
        for match in self.address_pattern_a.finditer(text):
            raw_spans.append((match.start(), match.end()))

        # Try Pattern B matches
        for match in self.address_pattern_b.finditer(text):
            raw_spans.append((match.start(), match.end()))

        # Try Postal Code + Lookback heuristic
        for match in self.postal_code_pattern.finditer(text):
            pc_start = match.start()
            pc_end = match.end()
            
            # Scan lookback window of 60 characters before the postal code
            lookback_start = max(0, pc_start - 60)
            context = text[lookback_start:pc_start]

            # Find all word-boundary indicator matches in context
            indicator_matches = list(self.indicator_pattern.finditer(context))
            if indicator_matches:
                # Find the earliest indicator position
                earliest_match = indicator_matches[0]
                earliest_idx = lookback_start + earliest_match.start()

                # Include any house/flat numbers directly preceding the indicator
                while earliest_idx > 0 and (text[earliest_idx - 1].isdigit() or text[earliest_idx - 1] in " #,-/"):
                    earliest_idx -= 1

                raw_spans.append((earliest_idx, pc_end))

        # Merge overlapping/adjacent address spans
        resolved_spans = self._resolve_address_overlaps(raw_spans)

        for start, end in resolved_spans:
            addr_raw = text[start:end]
            addr_text = addr_raw.strip()
            if not addr_text:
                continue

            # Adjust indices for stripped leading/trailing spaces
            leading_spaces = len(addr_raw) - len(addr_raw.lstrip())
            trailing_spaces = len(addr_raw) - len(addr_raw.rstrip())
            final_start = start + leading_spaces
            final_end = end - trailing_spaces

            # Basic sanity check: make sure the address consists of at least 3 words
            if len(addr_text.split()) >= 3:
                entities.append(PIIEntity(
                    entity_type=PIIType.ADDRESS,
                    original_text=addr_text,
                    start=final_start,
                    end=final_end,
                    confidence=0.75,
                    source_detector="contextual_address"
                ))

        return entities

    def _resolve_address_overlaps(self, spans: List[tuple]) -> List[tuple]:
        """
        Combines overlapping and adjacent coordinate spans.
        """
        if not spans:
            return []

        # Sort by start coordinate
        sorted_spans = sorted(spans, key=lambda s: s[0])
        merged = []

        curr_start, curr_end = sorted_spans[0][0], sorted_spans[0][1]

        for next_start, next_end in sorted_spans[1:]:
            # If overlap or adjacent (e.g. next_start <= curr_end + 2)
            if next_start <= curr_end + 2:
                if next_end > curr_end:
                    curr_end = next_end
            else:
                merged.append((curr_start, curr_end))
                curr_start, curr_end = next_start, next_end

        merged.append((curr_start, curr_end))
        return merged
