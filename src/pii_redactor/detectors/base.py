from abc import ABC, abstractmethod
from typing import List

from pii_redactor.models import DocumentBlock, PIIEntity

class BaseDetector(ABC):
    """
    Abstract base class defining the contract for all PII detectors.
    """

    @abstractmethod
    def detect(self, block: DocumentBlock) -> List[PIIEntity]:
        """
        Scans a DocumentBlock and returns a list of detected PIIEntity objects.
        """
        pass
