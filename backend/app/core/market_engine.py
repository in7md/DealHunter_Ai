import statistics
import aiosqlite
from typing import Optional, Tuple
from app.database.models import RawListing

class MarketEngine:
    @staticmethod
    async def get_dynamic_base_market_value(listing: RawListing, db: aiosqlite.Connection) -> Tuple[float, bool]:
        """
        Returns a tuple of (Base Market Value, is_fallback)
        """
        # Query for matching make, model, and year range
        query = """
            SELECT price_bhd FROM deals 
            WHERE make = ? AND model = ? AND year >= ? AND year <= ?
        """
        async with db.execute(query, (listing.make, listing.model, listing.year - 1, listing.year + 1)) as cursor:
            rows = await cursor.fetchall()
            
        prices = [row['price_bhd'] for row in rows if row['price_bhd'] and row['price_bhd'] > 0]
        
        # Include current listing in the calculation if we want, but better to just use historical.
        # But for outlier rejection to work smoothly, let's just use historical prices.
        
        if len(prices) >= 4:
            # Sort prices to calculate Q1 and Q3
            prices.sort()
            n = len(prices)
            
            # Simple Quartile Calculation
            def median(lst):
                return statistics.median(lst)
                
            mid = n // 2
            if n % 2 == 0:
                q1 = median(prices[:mid])
                q3 = median(prices[mid:])
            else:
                q1 = median(prices[:mid])
                q3 = median(prices[mid+1:])
                
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            
            cleaned_prices = [p for p in prices if lower_bound <= p <= upper_bound]
            
            if len(cleaned_prices) >= 3:
                return statistics.median(cleaned_prices), False
                
        # If we fall through here, either < 4 prices initially, or < 3 after cleaning
        if len(prices) >= 3:
            return statistics.median(prices), False
            
        # Smart Fallback
        return listing.price_bhd * 1.10, True
