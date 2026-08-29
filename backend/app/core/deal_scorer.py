from datetime import datetime
import aiosqlite
from app.database.models import RawListing, ScoredDeal
from app.core.deduplicator import Deduplicator
from app.core.market_engine import MarketEngine

HIGH_DEMAND = {"Toyota", "Lexus", "Honda", "Nissan", "Hyundai"}

AGENCY_KEYWORDS = ["وكالة البحرين", "وكالة", "وارد وكالة", "خليجي", "صبغ وكالة", "بحالة الوكالة"]
IMPORT_KEYWORDS = ["وارد أمريكا", "وارد امريكا", "وارد كندا", "وارد اليابان", "أمريكي", "امريكي"]
INSURED_KEYWORDS = ["بيمة وفحص", "مسجل ومأمن", "بيمه وفحص", "التسجيل ساري"]
NEEDS_INSPECT = ["بدون بيمة", "يحتاج فحص", "بدون فحص", "مطلوب تأمين"]
NEGOTIATION_KEYWORDS = ["urgent", "negotiable", "traveling", "مستعجل", "للبيع المستعجل", "قابل للتفاوض", "السفر"]


class DealScorer:
    async def score_deal(self, listing: RawListing, db: aiosqlite.Connection) -> ScoredDeal | None:
        if listing.price_bhd is None or listing.price_bhd <= 0:
            return None
        if listing.year < 1995:
            return None
        if listing.price_bhd < 250:
            return None

        text = f"{listing.description or ''} {listing.title or ''}"
        current_year = datetime.now().year
        
        # 1. Dynamic Base Market Value
        raw_market_median, is_fallback = await MarketEngine.get_dynamic_base_market_value(listing, db)

        # 2. Mileage Formula
        expected_mileage = (current_year - listing.year) * 20000.0
        if listing.mileage_km is not None and listing.mileage_km >= 0:
            actual_mileage = float(listing.mileage_km)
        else:
            actual_mileage = expected_mileage

        mileage_difference = expected_mileage - actual_mileage
        raw_adjustment_percentage = (mileage_difference / 20000.0) * 0.02
        
        # Clamp between -15% and +15%
        mileage_adjustment = max(-0.15, min(0.15, raw_adjustment_percentage))

        # 3. Adjusted Market Value
        adjusted_market_value = round(raw_market_median * (1 + mileage_adjustment))

        estimated_repairs = 200
        safety_buffer = 100
        if any(kw in text for kw in NEEDS_INSPECT):
            estimated_repairs += 120
        if any(kw in text for kw in INSURED_KEYWORDS):
            estimated_repairs = max(80, estimated_repairs - 80)

        estimated_costs = estimated_repairs + safety_buffer
        # Margin Rule and Ceiling Rule
        if listing.price_bhd >= adjusted_market_value:
            net_profit = 0.0
            score_price = 0.0
            score_margin = 0.0
        else:
            net_profit = round(adjusted_market_value - listing.price_bhd - estimated_repairs)
            discount_ratio = (adjusted_market_value - listing.price_bhd) / adjusted_market_value
            score_price = min(30.0, max(0.0, discount_ratio * 150.0))
            score_margin = min(25.0, max(0.0, (net_profit / 1000.0) * 25.0))

        data_completeness = 0
        if listing.mileage_km is not None and listing.mileage_km >= 0:
            data_completeness += 1
        if listing.description and len(listing.description) > 10:
            data_completeness += 1
        if listing.price_bhd > 500:
            data_completeness += 1
        if listing.phone:
            data_completeness += 1
        score_confidence = (data_completeness / 4.0) * 15.0
        
        if is_fallback:
            # dynamically flag confidence < 40% (max 5 out of 15)
            score_confidence = min(score_confidence, 5.0)

        score_velocity = 10.0 if listing.make in HIGH_DEMAND else 5.0

        if any(kw in text for kw in ("صبغ وكالة", "بحالة الوكالة")):
            score_repairs = 10.0
        else:
            score_repairs = 10.0 if estimated_repairs <= 200 else max(0.0, 10.0 - ((estimated_repairs - 200) / 50.0))

        score_negotiation = 0.0
        lowered = text.lower()
        if any(kw in lowered for kw in NEGOTIATION_KEYWORDS):
            score_negotiation = 10.0

        total_score = min(100.0, max(0.0, (
            score_price
            + score_margin
            + score_confidence
            + score_velocity
            + score_repairs
            + score_negotiation
        )))

        # The Ceiling Rule Cap
        if listing.price_bhd >= adjusted_market_value:
            total_score = min(total_score, 30.0)

        fingerprint_hash = Deduplicator.generate_fingerprint(listing)

        return ScoredDeal(
            fingerprint_hash=fingerprint_hash,
            listing=listing,
            market_median=raw_market_median,
            expected_mileage=expected_mileage,
            mileage_adjustment=mileage_adjustment,
            adjusted_market_value=adjusted_market_value,
            estimated_costs=estimated_costs,
            net_profit=net_profit,
            score_price=score_price,
            score_margin=score_margin,
            score_confidence=score_confidence,
            score_velocity=score_velocity,
            score_repairs=score_repairs,
            score_negotiation=score_negotiation,
            total_score=total_score,
        )
