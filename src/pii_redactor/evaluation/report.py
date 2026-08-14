import logging
from pii_redactor.evaluation.evaluator import EvaluationResult

logger = logging.getLogger(__name__)

def generate_markdown_report(result: EvaluationResult, output_path: str) -> None:
    """
    Generates a formal markdown evaluation report and writes it to the output path.
    """
    lines = []
    lines.append("# PII Redactor - Performance Evaluation Report\n")
    
    lines.append("## 1. Executive Summary\n")
    lines.append("This report evaluates the automatic detection performance of the PII Redaction Tool "
                 "against a manually annotated ground-truth benchmark dataset.\n")
    
    metrics = result.overall_metrics
    lines.append(f"*   **Overall Precision**: `{metrics.precision:.4f}`")
    lines.append(f"*   **Overall Recall**: `{metrics.recall:.4f}`")
    lines.append(f"*   **Overall F1-Score**: `{metrics.f1:.4f}`")
    lines.append(f"*   **Overall Accuracy**: `{metrics.accuracy:.4f}`")
    lines.append(f"*   **True Positives (TP)**: `{metrics.tp}`")
    lines.append(f"*   **False Positives (FP)**: `{metrics.fp}`")
    lines.append(f"*   **False Negatives (FN)**: `{metrics.fn}`\n")
    
    lines.append("## 2. Per-PII-Type Metrics\n")
    lines.append("| PII Type | Precision | Recall | F1-Score | Accuracy | TP | FP | FN |")
    lines.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
    
    for pii_type, m in sorted(result.per_type_metrics.items()):
        lines.append(
            f"| **{pii_type}** | {m.precision:.4f} | {m.recall:.4f} | {m.f1:.4f} | "
            f"{m.accuracy:.4f} | {m.tp} | {m.fp} | {m.fn} |"
        )
    lines.append("")

    lines.append("## 3. False Positives (Detections not in Ground Truth)\n")
    if not result.false_positives:
        lines.append("*No False Positives identified (Perfect Precision).*\n")
    else:
        lines.append("| Block ID | PII Type | Detected Text | Character Span |")
        lines.append("| :--- | :--- | :--- | :---: |")
        for fp in result.false_positives:
            lines.append(f"| `{fp.block_id}` | `{fp.entity_type}` | `{fp.text}` | `{fp.start}-{fp.end}` |")
        lines.append("")

    lines.append("## 4. False Negatives (Ground Truth PII Missed)\n")
    if not result.false_negatives:
        lines.append("*No False Negatives identified (Perfect Recall).*\n")
    else:
        lines.append("| Block ID | PII Type | Missed Text | Character Span |")
        lines.append("| :--- | :--- | :--- | :---: |")
        for fn in result.false_negatives:
            lines.append(f"| `{fn.block_id}` | `{fn.entity_type}` | `{fn.text}` | `{fn.start}-{fn.end}` |")
        lines.append("")

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        logger.info(f"Successfully generated markdown evaluation report at {output_path}")
    except Exception as e:
        logger.error(f"Failed to write evaluation report to {output_path}: {e}")
        raise IOError(f"Could not generate report file: {e}") from e
