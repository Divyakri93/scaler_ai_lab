import json
import logging
from typing import Dict, List, Set, Tuple
from pydantic import BaseModel, Field

from pii_redactor.models import PIIEntity, PIIType

logger = logging.getLogger(__name__)

class PIIMetrics(BaseModel):
    """
    Holds performance evaluation metrics for PII detection.
    """
    tp: int = 0
    fp: int = 0
    fn: int = 0
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    accuracy: float = 0.0

    def calculate(self) -> None:
        """
        Calculates precision, recall, F1, and accuracy from TP, FP, FN.
        """
        total_predictions = self.tp + self.fp
        self.precision = self.tp / total_predictions if total_predictions > 0 else 1.0

        total_ground_truth = self.tp + self.fn
        self.recall = self.tp / total_ground_truth if total_ground_truth > 0 else 1.0

        precision_plus_recall = self.precision + self.recall
        self.f1 = (2 * self.precision * self.recall) / precision_plus_recall if precision_plus_recall > 0 else 0.0

        total_cases = self.tp + self.fp + self.fn
        self.accuracy = self.tp / total_cases if total_cases > 0 else 1.0

class ErrorDetail(BaseModel):
    """
    Holds details of an evaluation error (false positive or false negative).
    """
    block_id: str
    entity_type: str
    text: str
    start: int
    end: int

class EvaluationResult(BaseModel):
    """
    Structured outcome of the evaluation run.
    """
    overall_metrics: PIIMetrics
    per_type_metrics: Dict[str, PIIMetrics]
    false_positives: List[ErrorDetail] = Field(default_factory=list)
    false_negatives: List[ErrorDetail] = Field(default_factory=list)

    @property
    def overall_precision(self) -> float:
        return self.overall_metrics.precision

    @property
    def overall_recall(self) -> float:
        return self.overall_metrics.recall

    @property
    def overall_f1(self) -> float:
        return self.overall_metrics.f1

class Evaluator:
    """
    Compares pipeline detections against annotated ground truth to generate metrics.
    """

    def __init__(self, ground_truth_path: str) -> None:
        self.ground_truth_path = ground_truth_path
        self.ground_truth_blocks = self._load_ground_truth()

    def _load_ground_truth(self) -> Dict[str, List[dict]]:
        """
        Loads and parses ground truth file.
        """
        try:
            with open(self.ground_truth_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info(f"Loaded ground truth from {self.ground_truth_path}.")
            return data.get("blocks", {})
        except Exception as e:
            logger.error(f"Failed to load ground truth from {self.ground_truth_path}: {e}")
            raise IOError(f"Could not read ground-truth dataset: {e}") from e

    def evaluate(self, detections: Dict[str, List[PIIEntity]]) -> EvaluationResult:
        """
        Computes precision, recall, F1, and error details comparing detections vs GT.
        """
        # Dictionary of PII types -> PIIMetrics to accumulate TPs, FPs, FNs
        per_type_accumulators: Dict[str, PIIMetrics] = {
            t.value: PIIMetrics() for t in PIIType
        }

        false_positives: List[ErrorDetail] = []
        false_negatives: List[ErrorDetail] = []

        # We union all block IDs from GT and detections to make sure we scan everything
        all_block_ids = set(self.ground_truth_blocks.keys()) | set(detections.keys())

        for block_id in all_block_ids:
            gts = self.ground_truth_blocks.get(block_id, [])
            dets = detections.get(block_id, [])

            matched_gts: Set[int] = set()
            matched_dets: Set[int] = set()

            # 1. Look for Exact Matches (TPs)
            for det_idx, det in enumerate(dets):
                for gt_idx, gt in enumerate(gts):
                    if gt_idx in matched_gts:
                        continue
                    
                    # Exact Match: same type, start, and end indices
                    if (det.entity_type.value == gt["type"] and 
                        det.start == gt["start"] and 
                        det.end == gt["end"]):
                        
                        matched_gts.add(gt_idx)
                        matched_dets.add(det_idx)
                        
                        # Increment TP
                        per_type_accumulators[det.entity_type.value].tp += 1
                        break

            # 2. Add unmatched detections as False Positives
            for det_idx, det in enumerate(dets):
                if det_idx not in matched_dets:
                    per_type_accumulators[det.entity_type.value].fp += 1
                    false_positives.append(ErrorDetail(
                        block_id=block_id,
                        entity_type=det.entity_type.value,
                        text=det.original_text,
                        start=det.start,
                        end=det.end
                    ))

            # 3. Add unmatched ground truths as False Negatives
            for gt_idx, gt in enumerate(gts):
                if gt_idx not in matched_gts:
                    per_type_accumulators[gt["type"]].fn += 1
                    false_negatives.append(ErrorDetail(
                        block_id=block_id,
                        entity_type=gt["type"],
                        text=gt["text"],
                        start=gt["start"],
                        end=gt["end"]
                    ))

        # 4. Calculate metrics for each PII type and aggregate overall metrics
        overall = PIIMetrics()
        final_per_type: Dict[str, PIIMetrics] = {}

        for pii_type_str, metrics in per_type_accumulators.items():
            metrics.calculate()
            final_per_type[pii_type_str] = metrics
            
            overall.tp += metrics.tp
            overall.fp += metrics.fp
            overall.fn += metrics.fn

        overall.calculate()

        return EvaluationResult(
            overall_metrics=overall,
            per_type_metrics=final_per_type,
            false_positives=false_positives,
            false_negatives=false_negatives
        )
