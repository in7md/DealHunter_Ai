from abc import ABC, abstractmethod
from typing import AsyncGenerator
from app.database.models import RawListing

class BaseAdapter(ABC):
    @abstractmethod
    async def fetch_listings(self) -> AsyncGenerator[RawListing, None]:
        pass
