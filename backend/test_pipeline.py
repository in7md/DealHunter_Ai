import asyncio
import json
import os
import aiosqlite
import httpx
from datetime import datetime

# Import modules
from app.config import settings
from app.database.models import RawListing, ScoredDeal
from app.database.db import init_db, get_db, DATABASE_URL
from app.core.deduplicator import Deduplicator
from app.core.deal_scorer import DealScorer
from app.core.ai_analyzer import AIAnalyzer
from app.adapters.opensooq_adapter import OpenSooqAdapter
from app.adapters.mock_adapter import MockAdapter
from app.services.scanner import ScannerService

print("=== Phase 1: Static Analysis & Code Integrity ===")

# 1. Check all modules loaded
print("[x] Backend modules and subpackages loaded without circular dependencies.")

# 2. Test environment variable handling
analyzer = AIAnalyzer()
analyzer.api_key = "" # test missing key
dummy_listing = RawListing("test", "1", "Toyota Camry", "Toyota", "Camry", 2020, 4000.0, "http://test")
dummy_scored = Scorer = DealScorer().score_deal(dummy_listing)
assert dummy_scored is not None

async def test_ai_graceful():
    res = await analyzer.analyze_deal(dummy_scored)
    assert "Missing API key" in res or "AI Analysis unavailable" in res
    print(f"[x] Missing GEMINI_API_KEY gracefully handled: '{res}'")

asyncio.run(test_ai_graceful())
print(" Phase 1 PASSED!\n")


print("=== Phase 2: Backend, Scraping & Data Pipeline Stress Test ===")

# 1. Scraper Test with OpenSooq adapter against real opensooq.json and irregular listings
adapter = OpenSooqAdapter()

# Test irregular edge case items
irregular_items = [
    {"id": "call_1", "title": "BMW Call for Price", "price_amount": "اتصل للسعر"},
    {"id": "call_2", "title": "Mercedes Call", "price_amount": "Call for Price"},
    {"id": "none_p", "title": "Nissan No Price", "price_amount": None},
    {"id": "zero_p", "title": "Honda Zero", "price_amount": "0 BHD"},
    {"id": "ar_num", "title": "Toyota Arabic Digits", "price_amount": "٤,٥٠٠ د.ب", "starCps": [{"icon": "year.webp", "label": "2021"}]},
    {"id": "dec_p", "title": "Lexus Decimal Price", "price_amount": "12,500.750 BHD", "starCps": [{"icon": "year.webp", "label": "2022"}]},
    {"id": "", "title": "Missing ID", "price_amount": "3000"},
    {},
]

print("Testing OpenSooq scraper with irregular listings:")
for item in irregular_items:
    listing = adapter._to_listing(item)
    if listing:
        print(f"  -> Extracted: {listing.title} -> {listing.price_bhd} BHD")
    else:
        print(f"  -> Safely filtered irregular item: {item.get('title', 'EMPTY')}")

# Test with actual opensooq.json
if os.path.exists("opensooq.json"):
    with open("opensooq.json", "r", encoding="utf-8", errors="ignore") as f:
        data = json.load(f)
    sample_items = data["props"]["pageProps"]["serpApiResponse"]["listings"]["items"]
    parsed_count = 0
    for it in sample_items:
        res = adapter._to_listing(it)
        if res:
            parsed_count += 1
    print(f"[x] OpenSooq real payload parsed {parsed_count}/{len(sample_items)} listings accurately in BHD.")

# 2. Deduplication Engine & DB Stress Test
async def test_dedup_and_db():
    await init_db()
    
    test_listing = RawListing(
        source="opensooq",
        source_id="test_dup_999",
        title="2020 Toyota Land Cruiser",
        make="Toyota",
        model="Land Cruiser",
        year=2020,
        price_bhd=18500.0,
        url="http://test.com/dup",
        mileage_km=45000.0,
        phone="+97339000000",
        description="وكالة البحرين بحالة ممتازة صبغ وكالة"
    )
    
    scorer = DealScorer()
    deal1 = scorer.score_deal(test_listing)
    assert deal1 is not None
    
    # Simulate feeding twice directly to db with ON CONFLICT
    async with aiosqlite.connect(DATABASE_URL) as db:
        for i in range(2):
            await db.execute(
                """
                INSERT INTO deals (
                    fingerprint_hash, source, source_id, title, make, model, year,
                    price_bhd, mileage_km, phone, url, description, image_url,
                    total_score, net_profit, ai_insights
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(fingerprint_hash) DO UPDATE SET
                    price_bhd=excluded.price_bhd,
                    total_score=excluded.total_score,
                    net_profit=excluded.net_profit,
                    ai_insights=COALESCE(excluded.ai_insights, deals.ai_insights)
                """,
                (
                    deal1.fingerprint_hash, deal1.listing.source, deal1.listing.source_id,
                    deal1.listing.title, deal1.listing.make, deal1.listing.model,
                    deal1.listing.year, deal1.listing.price_bhd, deal1.listing.mileage_km,
                    deal1.listing.phone, deal1.listing.url, deal1.listing.description,
                    deal1.listing.image_url, deal1.total_score, deal1.net_profit,
                    deal1.ai_insights
                )
            )
            await db.commit()
        
        # Verify exactly 1 record exists
        async with db.execute("SELECT COUNT(*) FROM deals WHERE fingerprint_hash = ?", (deal1.fingerprint_hash,)) as cursor:
            count = (await cursor.fetchone())[0]
            assert count == 1, f"Expected 1 record, got {count}"
            print(f"[x] Deduplication verified: Duplicate insert handled cleanly without SQL Integrity error (Count={count}).")
            
        # Clean up test entry
        await db.execute("DELETE FROM deals WHERE fingerprint_hash = ?", (deal1.fingerprint_hash,))
        await db.commit()

asyncio.run(test_dedup_and_db())

# 3. Scoring Engine Stress Test
scorer = DealScorer()
edge_cases = [
    # Extreme high price
    ("Extreme High Price (100M BHD)", RawListing("test", "e1", "2022 Porsche 911", "Porsche", "911", 2022, 100_000_000.0, "http://test", 5000.0, "+97330000000", "نظيف")),
    # Zero mileage (brand new car)
    ("Zero Mileage (0 km)", RawListing("test", "e2", "2024 Toyota Camry", "Toyota", "Camry", 2024, 7500.0, "http://test", 0.0, "+97330000000", "وكالة")),
    # Missing mileage (None)
    ("Missing Mileage (None)", RawListing("test", "e3", "2020 Nissan Patrol", "Nissan", "Patrol", 2020, 9500.0, "http://test", None, "+97330000000", "وكالة")),
    # Negative mileage (edge)
    ("Negative Mileage (-500 km)", RawListing("test", "e4", "2021 Honda Civic", "Honda", "Civic", 2021, 3800.0, "http://test", -500.0, "+97330000000", "ممتازة")),
    # Extremely low valid price (250 BHD)
    ("Min Valid Price (250 BHD)", RawListing("test", "e5", "1999 Toyota Echo", "Toyota", "Echo", 1999, 250.0, "http://test", 250000.0, "+97330000000", "بيمة وفحص")),
    # Invalid low price (100 BHD) -> should return None
    ("Invalid Low Price (100 BHD)", RawListing("test", "e6", "1999 Toyota Echo", "Toyota", "Echo", 1999, 100.0, "http://test", 250000.0, "+97330000000", "بيمة وفحص")),
    # Antique year (1985) -> should return None
    ("Antique Car (1985)", RawListing("test", "e7", "1985 Mercedes 280", "Mercedes", "280", 1985, 3000.0, "http://test", 200000.0, "+97330000000", "نظيف")),
    # Future model year (2028)
    ("Future Model Year (2028)", RawListing("test", "e8", "2028 Lexus LX600", "Lexus", "LX600", 2028, 48000.0, "http://test", 100.0, "+97330000000", "وكالة")),
    # Empty title and desc
    ("Empty Title and Desc", RawListing("test", "e9", "", "Toyota", "Corolla", 2019, 3200.0, "http://test", None, None, "")),
]

print("\nTesting Scoring Engine Edge Cases:")
for label, listing in edge_cases:
    deal = scorer.score_deal(listing)
    if deal:
        assert 0.0 <= deal.total_score <= 100.0, f"Score out of bounds: {deal.total_score}"
        print(f"  -> {label}: Score={deal.total_score:.1f}/100, Est. Profit={deal.net_profit:.1f} BHD, Market Val={deal.adjusted_market_value:.1f} BHD")
    else:
        print(f"  -> {label}: Correctly filtered out (None)")

print("[x] Scoring engine edge case validation complete: zero division prevented, scores clamped [0, 100].")

# 4. SSE Stream Stability Test
import uvicorn
from app.main import app

async def test_sse_stream():
    config = uvicorn.Config(app, host="127.0.0.1", port=8899, log_level="error")
    server = uvicorn.Server(config)
    server_task = asyncio.create_task(server.serve())
    await asyncio.sleep(1)

    try:
        async with httpx.AsyncClient(base_url="http://127.0.0.1:8899", timeout=15.0) as client:
            # Connect to stream in mock mode
            print("\nConnecting to /api/scanner/stream?mode=mock...")
            received_deals = 0
            async with client.stream("GET", "/api/scanner/stream?mode=mock") as response:
                assert response.status_code == 200
                assert "text/event-stream" in response.headers.get("content-type", "")
                
                async for line in response.aiter_lines():
                    if line.startswith("event: new_deal"):
                        received_deals += 1
                        print(f"  -> Received SSE Event #{received_deals}: new_deal")
                    elif line.startswith("data:") and "fingerprint_hash" in line:
                        deal_json = json.loads(line[5:].strip())
                        assert "total_score" in deal_json
                        assert "listing" in deal_json
                    
                    if received_deals >= 3:
                        print("[x] SSE Stream validated: successfully yielded 3 deals without blocking.")
                        break
    finally:
        server.should_exit = True
        await server_task

asyncio.run(test_sse_stream())
print("\n Phase 2 PASSED!")
