import logging
from typing import List

from pii_redactor.detectors.base import BaseDetector
from pii_redactor.detectors.regex_detector import RegexDetector
from pii_redactor.detectors.ner_detector import NERDetector
from pii_redactor.detectors.contextual_detector import ContextualDetector
from pii_redactor.models import DocumentBlock, PIIEntity

logger = logging.getLogger(__name__)

class DetectionAggregator:
    """
    Coordinates PII detection across multiple detectors and resolves overlapping
    conflicts using a deterministic, priority-based interval selection algorithm.
    """

    def __init__(self, detectors: List[BaseDetector] = None) -> None:
        if detectors is None:
            # Order: contextual first, regex, then NER. This allows contextual
            # and regex to populate first.
            self.detectors = [
                ContextualDetector(),
                RegexDetector(),
                NERDetector()
            ]
        else:
            self.detectors = detectors

    def detect(self, block: DocumentBlock) -> List[PIIEntity]:
        """
        Runs all configured detectors on the block and resolves overlaps.
        """
        candidates: List[PIIEntity] = []

        for detector in self.detectors:
            try:
                detections = detector.detect(block)
                candidates.extend(detections)
            except Exception as e:
                logger.error(
                    f"Detector {detector.__class__.__name__} failed on block {block.block_id}: {e}"
                )

        return self.resolve_conflicts(candidates)

    def resolve_conflicts(self, candidates: List[PIIEntity]) -> List[PIIEntity]:
        """
        Resolves overlapping intervals.
        Prioritizes:
        1. Higher confidence (descending)
        2. Longer span length (descending)
        3. Deterministic tiebreakers: start index (ascending) and entity type name (alphabetical)
        """
        if not candidates:
            return []

        # Sort candidates according to priority
        # Note: we use negative for descending values
        sorted_candidates = sorted(
            candidates,
            key=lambda e: (-e.confidence, -(e.end - e.start), e.start, e.entity_type)
        )

        accepted: List[PIIEntity] = []

        for candidate in sorted_candidates:
            overlaps = False
            for acc in accepted:
                # Check overlap between [candidate.start, candidate.end) and [acc.start, acc.end)
                if max(candidate.start, acc.start) < min(candidate.end, acc.end):
                    overlaps = True
                    logger.debug(
                        f"[Conflict Resolution] Discarded candidate {candidate.entity_type} "
                        f"({candidate.start}-{candidate.end}) in favor of accepted "
                        f"{acc.entity_type} ({acc.start}-{acc.end})."
                    )
                    break
            
            if not overlaps:
                accepted.append(candidate)

        # Sort accepted entities back into text order (ascending start offset)
        return sorted(accepted, key=lambda e: e.start)
