import logging
from typing import Optional

from pii_redactor.models import PIIEntity, PIIType
from pii_redactor.replacement.faker_provider import FakerProvider
from pii_redactor.replacement.mapping_store import MappingStore

logger = logging.getLogger(__name__)

class ReplacementEngine:
    """
    Coordinates replacement generation, checking caches for consistency
    and performing cross-entity name-to-email formatting alignments.
    """

    def __init__(
        self,
        seed: Optional[int] = None,
        mapping_store: Optional[MappingStore] = None
    ) -> None:
        self.provider = FakerProvider(seed=seed)
        self.store = mapping_store if mapping_store is not None else MappingStore()

    def get_replacement(self, entity: PIIEntity) -> str:
        """
        Retrieves or generates a consistent synthetic replacement for a PIIEntity.
        """
        # 1. Check direct cache lookup
        cached = self.store.get(entity.original_text)
        if cached is not None:
            return cached

        # 2. Check for Email & Name alignment
        if entity.entity_type == PIIType.EMAIL:
            try:
                local_part, _ = entity.original_text.split("@", 1)
                mapped_local = self.store.map_email_local_part(local_part)
                
                # If local part changed, it means we matched some name parts
                if mapped_local != local_part:
                    replacement = f"{mapped_local}@example.com"
                    self.store.set(entity.original_text, replacement)
                    logger.debug(
                        f"Aligned email replacement consistently: "
                        f"{entity.original_text} -> {replacement}"
                    )
                    return replacement
            except Exception as e:
                logger.debug(f"Failed to align email consistently: {e}")

        # 3. Cache Miss: Generate a fresh synthetic value
        replacement = self.provider.generate(entity.entity_type, entity.original_text)
        self.store.set(entity.original_text, replacement)

        # 4. If Name PII, extract and store name parts to support future email alignments
        if entity.entity_type == PIIType.FULL_NAME:
            self.store.add_name_parts(entity.original_text, replacement)

        return replacement
