import re
from typing import Dict, Optional

class MappingStore:
    """
    Caches PII replacements to maintain consistency across the document.
    Also tracks name part mappings to support cross-entity alignment (Name -> Email).
    """

    def __init__(self) -> None:
        # Maps normalized raw PII text -> synthetic replacement
        self._mappings: Dict[str, str] = {}
        # Maps normalized individual name parts -> synthetic name parts
        # e.g., "rashi" -> "john", "patil" -> "doe"
        self._part_mappings: Dict[str, str] = {}

    def _normalize_key(self, text: str) -> str:
        """
        Strips whitespace and converts to lowercase to ensure robust lookup.
        """
        return re.sub(r"\s+", " ", text.strip().lower())

    def get(self, text: str) -> Optional[str]:
        """
        Retrieves a cached replacement if it exists.
        """
        key = self._normalize_key(text)
        return self._mappings.get(key)

    def set(self, text: str, replacement: str) -> None:
        """
        Caches a new replacement.
        """
        key = self._normalize_key(text)
        self._mappings[key] = replacement

    def add_name_parts(self, raw_name: str, replacement_name: str) -> None:
        """
        Extracts words from raw and replacement names, mapping them 1-to-1
        to enable aligned email generation.
        """
        # Extract word parts
        raw_parts = [p.lower() for p in re.findall(r"\w+", raw_name) if len(p) > 1]
        rep_parts = [p.lower() for p in re.findall(r"\w+", replacement_name) if len(p) > 1]

        # Only map if part counts align (e.g., "Alice Smith" -> "John Doe" maps 2 parts)
        if len(raw_parts) == len(rep_parts):
            for raw_p, rep_p in zip(raw_parts, rep_parts):
                self._part_mappings[raw_p] = rep_p

    def map_email_local_part(self, local_part: str) -> str:
        """
        Splits an email's local part by delimiters, replaces any parts
        that match cached name parts, and rebuilds the string.
        """
        # Split using punctuation delimiters, keeping delimiters in the list
        tokens = re.split(r"([._%+-])", local_part)
        mapped_tokens = []

        for token in tokens:
            token_lower = token.lower()
            if token_lower in self._part_mappings:
                # Use cached name part replacement
                mapped_tokens.append(self._part_mappings[token_lower])
            else:
                mapped_tokens.append(token)

        return "".join(mapped_tokens)
