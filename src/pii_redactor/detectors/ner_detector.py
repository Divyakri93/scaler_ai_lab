import logging
from typing import List
import spacy

from pii_redactor.detectors.base import BaseDetector
from pii_redactor.models import DocumentBlock, PIIEntity, PIIType

logger = logging.getLogger(__name__)

class NERDetector(BaseDetector):
    """
    Named Entity Recognition (NER) detector using spaCy.
    Detects PERSON and ORG entities, mapping them to FULL_NAME and COMPANY_NAME.
    """

    def __init__(self, model_name: str = "en_core_web_sm") -> None:
        try:
            # Disable parser and lemmatizer to make NER pipeline fast
            self.nlp = spacy.load(model_name, disable=["parser", "lemmatizer"])
            logger.info(f"Successfully loaded spaCy model '{model_name}'.")
        except Exception as e:
            logger.error(f"Failed to load spaCy model '{model_name}': {e}. "
                         f"Please ensure it is downloaded via 'python -m spacy download {model_name}'")
            raise RuntimeError(f"spaCy model unavailable: {e}") from e

    def detect(self, block: DocumentBlock) -> List[PIIEntity]:
        """
        Runs spaCy NER on the document block text.
        """
        entities: List[PIIEntity] = []
        text = block.text

        if not text or not text.strip():
            return entities

        try:
            doc = self.nlp(text)
        except Exception as e:
            logger.error(f"spaCy execution failed on block '{block.block_id}': {e}")
            return entities

        for ent in doc.ents:
            original_text = ent.text
            start = ent.start_char
            end = ent.end_char

            if ent.label_ == "PERSON":
                # Only keep name if it has alphabetical characters (ignore empty or purely punctuation names)
                cleaned = original_text.strip()
                if cleaned and any(c.isalpha() for c in cleaned):
                    entities.append(PIIEntity(
                        entity_type=PIIType.FULL_NAME,
                        original_text=original_text,
                        start=start,
                        end=end,
                        confidence=0.85,
                        source_detector="spacy",
                        metadata={"spacy_label": "PERSON"}
                    ))

            elif ent.label_ == "ORG":
                cleaned = original_text.strip()
                if cleaned and any(c.isalpha() for c in cleaned):
                    entities.append(PIIEntity(
                        entity_type=PIIType.COMPANY_NAME,
                        original_text=original_text,
                        start=start,
                        end=end,
                        confidence=0.80,
                        source_detector="spacy",
                        metadata={"spacy_label": "ORG"}
                    ))
        
        return entities
