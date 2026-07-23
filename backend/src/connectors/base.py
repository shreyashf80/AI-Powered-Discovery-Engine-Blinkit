from abc import ABC, abstractmethod
from typing import List, Any
import logging

from src.shared.schemas import RawItem

logger = logging.getLogger(__name__)

class BaseConnector(ABC):
    @abstractmethod
    def get_source_name(self) -> str:
        """Return the canonical source name (e.g., 'reddit', 'play_store')"""
        pass

    @abstractmethod
    async def fetch(self, config: Any) -> List[RawItem]:
        """Fetch data and normalize to RawItem schema"""
        pass
