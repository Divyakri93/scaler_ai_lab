import logging
from typing import Dict, List
from docx import Document

from pii_redactor.models import DocumentBlock, PIIEntity

logger = logging.getLogger(__name__)

class DocxWriter:
    """
    Writes redactions back to the DOCX XML structure.
    Uses run-level splicing in descending offset order to avoid coordinate shifts
    and preserve font styles.
    """

    def __init__(self, reader: Document):
        # We reuse the Document object from the reader to maintain structure
        self.doc = reader

    def save(self, output_path: str) -> None:
        """
        Saves the modified document to the output path.
        """
        try:
            self.doc.save(output_path)
            logger.info(f"Successfully saved redacted DOCX to {output_path}")
        except Exception as e:
            logger.error(f"Failed to save redacted DOCX to {output_path}: {e}")
            raise IOError(f"Could not write output file: {e}") from e

    def redact(self, block_entities: Dict[str, List[PIIEntity]], blocks: List[DocumentBlock]) -> None:
        """
        Iterates over all blocks and applies their corresponding PIIEntity redactions.
        """
        for block in blocks:
            entities = block_entities.get(block.block_id, [])
            if not entities:
                continue

            self._redact_block(block, entities)

    def _redact_block(self, block: DocumentBlock, entities: List[PIIEntity]) -> None:
        """
        Applies redactions to a single DocumentBlock.
        Sorted in descending start index to prevent coordinate changes for preceding entities.
        """
        # Sort entities right-to-left
        sorted_entities = sorted(entities, key=lambda e: e.start, reverse=True)
        paragraph = block.element

        # Fallback: if block runs are missing but text exists, replace directly in paragraph
        if not block.runs:
            text = block.text
            for entity in sorted_entities:
                replacement = entity.replacement if entity.replacement is not None else f"[{entity.entity_type}]"
                text = text[:entity.start] + replacement + text[entity.end:]
            paragraph.text = text
            return

        # Regular: Run-level splicing to preserve styles
        for entity in sorted_entities:
            replacement = entity.replacement if entity.replacement is not None else f"[{entity.entity_type}]"

            # Identify runs intersecting [entity.start, entity.end)
            intersecting = []
            for r_info in block.runs:
                # Max of starts < Min of ends indicates overlap
                if max(r_info.start, entity.start) < min(r_info.end, entity.end):
                    intersecting.append(r_info)

            if not intersecting:
                continue

            first_r = intersecting[0]
            last_r = intersecting[-1]

            if len(intersecting) == 1:
                # Scenario 1: Entity is completely contained in a single run
                r_info = first_r
                rel_start = entity.start - r_info.start
                rel_end = entity.end - r_info.start
                prefix = r_info.run.text[:rel_start]
                suffix = r_info.run.text[rel_end:]
                r_info.run.text = prefix + replacement + suffix
                r_info.text = r_info.run.text
            else:
                # Scenario 2: Entity spans multiple runs
                # 1. Update the first run (keep prefix + add full replacement)
                rel_start = entity.start - first_r.start
                prefix = first_r.run.text[:rel_start]
                first_r.run.text = prefix + replacement
                first_r.text = first_r.run.text

                # 2. Clear all middle runs completely
                for mid_r in intersecting[1:-1]:
                    mid_r.run.text = ""
                    mid_r.text = ""

                # 3. Update the last run (keep suffix only)
                rel_end = entity.end - last_r.start
                suffix = last_r.run.text[rel_end:]
                last_r.run.text = suffix
                last_r.text = last_r.run.text
