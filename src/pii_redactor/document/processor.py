import logging
from typing import Callable, Dict, List, Optional

from pii_redactor.config import RedactorConfig
from pii_redactor.detectors.aggregator import DetectionAggregator
from pii_redactor.document.reader import DocxReader
from pii_redactor.document.writer import DocxWriter
from pii_redactor.models import DocumentBlock, PIIEntity
from pii_redactor.replacement.replacement_engine import ReplacementEngine

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """
    Orchestrates the lifecycle of the document redaction:
    1. Reads the document blocks using DocxReader.
    2. Delegates detection and replacement to the passed redactor callback.
    3. Writes modified blocks using DocxWriter.
    4. Saves the final redacted file.
    """

    def process(
        self,
        input_path: str,
        output_path: str,
        redact_callback: Callable[[List[DocumentBlock]], Dict[str, List[PIIEntity]]]
    ) -> None:
        """
        Runs the full document processing pipeline.
        
        Args:
            input_path: Path to the input DOCX file.
            output_path: Path to the target output DOCX file.
            redact_callback: A callable that accepts a list of DocumentBlocks
                             and returns a mapping of block_id to PIIEntity list.
        """
        logger.info(f"Starting document processing pipeline: {input_path} -> {output_path}")

        # 1. Read document
        reader = DocxReader(input_path)
        blocks = reader.read()

        # 2. Call the redaction pipeline
        logger.debug("Executing PII detection and replacement callback...")
        block_entities = redact_callback(blocks)

        # 3. Apply changes & save
        writer = DocxWriter(reader.doc)
        writer.redact(block_entities, blocks)
        writer.save(output_path)

        logger.info("Document processing pipeline completed successfully.")


class RedactionPipeline:
    """
    Coordinates config loading, PII detection, and consistent synthetic replacement
    across a document. Saves the redacted document to the output path.
    """

    def __init__(self, config: Optional[RedactorConfig] = None) -> None:
        self.config = config if config is not None else RedactorConfig()
        self.aggregator = DetectionAggregator()
        self.replacement_engine = ReplacementEngine(seed=self.config.seed)
        self.processor = DocumentProcessor()

    def redact(self, input_path: str, output_path: str) -> Dict[str, List[PIIEntity]]:
        """
        Runs the redaction pipeline on the input document, saving the redacted DOCX.
        Returns a dictionary of all redacted entities mapped by block ID.
        """
        all_redacted: Dict[str, List[PIIEntity]] = {}

        def redact_callback(blocks: List[DocumentBlock]) -> Dict[str, List[PIIEntity]]:
            block_entities = {}
            for block in blocks:
                # 1. Detect candidate PII
                candidates = self.aggregator.detect(block)
                
                # 2. Filter candidates based on confidence thresholds and generate replacements
                filtered_entities = []
                for entity in candidates:
                    threshold = self.config.get_threshold(entity.entity_type)
                    if entity.confidence >= threshold:
                        # Generate consistent mock replacement
                        replacement = self.replacement_engine.get_replacement(entity)
                        entity.replacement = replacement
                        filtered_entities.append(entity)
                        
                        # Store in global tracking dictionary
                        all_redacted.setdefault(block.block_id, []).append(entity)
                
                if filtered_entities:
                    block_entities[block.block_id] = filtered_entities
            
            return block_entities

        # Execute processing pipeline
        self.processor.process(input_path, output_path, redact_callback)
        return all_redacted
