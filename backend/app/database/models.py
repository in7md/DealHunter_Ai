from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass
class RawListing:
    source: str
    source_id: str
    title: str
    make: str
    model: str
    year: int
    price_bhd: float
    url: str
    mileage_km: Optional[float] = None
    phone: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    scraped_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class ScoredDeal:
    fingerprint_hash: str
    listing: RawListing
    market_median: float
    expected_mileage: float
    mileage_adjustment: float
    adjusted_market_value: float
    estimated_costs: float
    net_profit: float
    score_price: float
    score_margin: float
    score_confidence: float
    score_velocity: float
    score_repairs: float
    score_negotiation: float
    total_score: float
    ai_insights: Optional[str] = None
    is_gemini_analyzed: bool = False
    
    def dict(self):
        import dataclasses
        return dataclasses.asdict(self)
