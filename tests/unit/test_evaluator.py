import os
import json
import pytest
from pii_redactor.evaluation.evaluator import Evaluator
from pii_redactor.models import PIIEntity, PIIType

@pytest.fixture
def temp_ground_truth(tmp_path):
    """
    Creates a temporary ground truth file.
    """
    gt_data = {
        "document_id": "test_doc",
        "blocks": {
            "p_0": [
                {"type": "FULL_NAME", "text": "Alice Smith", "start": 0, "end": 11},
                {"type": "EMAIL", "text": "alice@test.com", "start": 15, "end": 29}
            ],
            "p_1": [
                {"type": "PHONE", "text": "123-456-7890", "start": 5, "end": 17}
            ]
        }
    }
    gt_path = os.path.join(tmp_path, "gt.json")
    with open(gt_path, "w", encoding="utf-8") as f:
        json.dump(gt_data, f)
    return gt_path

def test_evaluator_perfect_match(temp_ground_truth):
    evaluator = Evaluator(temp_ground_truth)

    # Detections that match ground truth exactly
    detections = {
        "p_0": [
            PIIEntity(entity_type=PIIType.FULL_NAME, original_text="Alice Smith", start=0, end=11, confidence=1.0, source_detector="test"),
            PIIEntity(entity_type=PIIType.EMAIL, original_text="alice@test.com", start=15, end=29, confidence=1.0, source_detector="test")
        ],
        "p_1": [
            PIIEntity(entity_type=PIIType.PHONE, original_text="123-456-7890", start=5, end=17, confidence=1.0, source_detector="test")
        ]
    }

    result = evaluator.evaluate(detections)

    assert result.overall_metrics.tp == 3
    assert result.overall_metrics.fp == 0
    assert result.overall_metrics.fn == 0
    assert result.overall_precision == 1.0
    assert result.overall_recall == 1.0
    assert result.overall_f1 == 1.0
    assert len(result.false_positives) == 0
    assert len(result.false_negatives) == 0

def test_evaluator_errors(temp_ground_truth):
    evaluator = Evaluator(temp_ground_truth)

    # 1. Full name is missing (FN)
    # 2. Email is detected correctly (TP)
    # 3. Phone is missing (FN)
    # 4. Extra entity "Bob" (GPE/Name) detected at index 40 (FP)
    detections = {
        "p_0": [
            PIIEntity(entity_type=PIIType.EMAIL, original_text="alice@test.com", start=15, end=29, confidence=1.0, source_detector="test"),
            PIIEntity(entity_type=PIIType.FULL_NAME, original_text="Bob", start=40, end=43, confidence=0.8, source_detector="test")
        ]
    }

    result = evaluator.evaluate(detections)

    # TP = 1 (email)
    # FP = 1 (Bob)
    # FN = 2 (Alice Smith, Phone in p_1)
    assert result.overall_metrics.tp == 1
    assert result.overall_metrics.fp == 1
    assert result.overall_metrics.fn == 2

    # Precision = 1 / (1 + 1) = 0.5
    # Recall = 1 / (1 + 2) = 0.3333
    assert result.overall_precision == 0.5
    assert pytest.approx(result.overall_recall, rel=1e-3) == 0.3333

    # Check error details
    assert len(result.false_positives) == 1
    assert result.false_positives[0].text == "Bob"
    assert result.false_positives[0].block_id == "p_0"

    assert len(result.false_negatives) == 2
    missed_texts = [fn.text for fn in result.false_negatives]
    assert "Alice Smith" in missed_texts
    assert "123-456-7890" in missed_texts
