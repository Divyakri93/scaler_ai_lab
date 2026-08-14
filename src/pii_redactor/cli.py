import argparse
import logging
import sys
import time
from typing import List, Optional

from pii_redactor.config import RedactorConfig
from pii_redactor.document.processor import RedactionPipeline
from pii_redactor.utils.logging import setup_logging

logger = logging.getLogger("pii_redactor_cli")

def parse_args(args: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Production-grade local PII Redaction Tool for DOCX files."
    )
    parser.add_argument(
        "-i", "--input",
        required=True,
        help="Path to the input DOCX file containing sensitive PII."
    )
    parser.add_argument(
        "-o", "--output",
        required=True,
        help="Path where the redacted DOCX file will be saved."
    )
    parser.add_argument(
        "-s", "--seed",
        type=int,
        default=None,
        help="Optional seed for the Faker random generator to guarantee determinism."
    )
    parser.add_argument(
        "-c", "--confidence-threshold",
        type=float,
        default=None,
        help="Overall confidence cutoff threshold (0.0 to 1.0) for redacting PII."
    )
    parser.add_argument(
        "--evaluate",
        action="store_true",
        help="Flag to run performance evaluation on the output."
    )
    parser.add_argument(
        "--ground-truth",
        default=None,
        help="Path to the ground truth JSON file for evaluation."
    )
    parser.add_argument(
        "--report",
        default=None,
        help="Path where the markdown evaluation report will be written."
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enables detailed debug logging level."
    )
    return parser.parse_args(args)

def main(args: Optional[List[str]] = None) -> int:
    if args is None:
        args = sys.argv[1:]
    
    parsed = parse_args(args)
    setup_logging(verbose=parsed.verbose)

    logger.info("Initializing PII Redactor...")
    start_time = time.time()

    # 1. Initialize configuration
    config = RedactorConfig()
    
    if parsed.seed is not None:
        config.seed = parsed.seed
    if parsed.confidence_threshold is not None:
        config.overall_threshold = parsed.confidence_threshold
    
    # 2. Run Redaction
    try:
        pipeline = RedactionPipeline(config=config)
        redacted_entities = pipeline.redact(parsed.input, parsed.output)
        
        # Calculate summary statistics
        total_redacted = 0
        categories_count = {}
        for block_id, entities in redacted_entities.items():
            total_redacted += len(entities)
            for entity in entities:
                categories_count[entity.entity_type.name] = categories_count.get(entity.entity_type.name, 0) + 1
        
        duration = time.time() - start_time
        logger.info(f"Redaction completed in {duration:.2f}s.")
        logger.info(f"Total PII entities redacted: {total_redacted}")
        
        for cat, count in categories_count.items():
            logger.info(f"  - {cat}: {count}")

    except Exception as e:
        logger.error(f"Redaction failed: {e}", exc_info=parsed.verbose)
        return 1

    # 3. Optional Evaluation
    if parsed.evaluate:
        logger.info("Starting performance evaluation...")
        # Evaluation engine hook will be integrated here in Phase 12
        if not parsed.ground_truth:
            logger.error("Error: --ground-truth is required when running with --evaluate.")
            return 1
        
        try:
            from pii_redactor.evaluation.evaluator import Evaluator
            from pii_redactor.evaluation.report import generate_markdown_report

            # Run evaluation against the redacted entities
            evaluator = Evaluator(ground_truth_path=parsed.ground_truth)
            metrics = evaluator.evaluate(redacted_entities)
            
            logger.info("Evaluation completed successfully.")
            logger.info(f"  Overall Precision: {metrics.overall_precision:.4f}")
            logger.info(f"  Overall Recall: {metrics.overall_recall:.4f}")
            logger.info(f"  Overall F1-Score: {metrics.overall_f1:.4f}")

            # Generate report if path specified
            if parsed.report:
                generate_markdown_report(metrics, parsed.report)
                logger.info(f"Evaluation report written to {parsed.report}")

        except Exception as e:
            logger.error(f"Evaluation failed: {e}", exc_info=parsed.verbose)
            return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
