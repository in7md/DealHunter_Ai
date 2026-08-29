import asyncio
import json
import hashlib
import random
from sse_starlette.sse import ServerSentEvent
from app.adapters.mock_adapter import MockAdapter
from app.adapters.opensooq_adapter import OpenSooqAdapter
from app.core.deal_scorer import DealScorer
from app.core.ai_analyzer import AIAnalyzer
from app.database.db import get_db

from app.adapters.instagram_adapter import InstagramAdapter
from app.adapters.yallamotor_adapter import YallaMotorAdapter
from app.adapters.dubizzle_adapter import DubizzleAdapter
from app.adapters.carsbh_adapter import CarsbhAdapter
from app.adapters.righcars_adapter import RighCarsAdapter
from app.adapters.facebook_adapter import FacebookAdapter

class ScannerService:
    def __init__(self):
        self.scorer = DealScorer()
        self.ai = AIAnalyzer()

    async def run_scan(self, sources_param: str = "opensooq,instagram,yallamotor,dubizzle,carsbh,righcars,facebook"):
        sources = [s.strip() for s in sources_param.split(",")]
        adapters = []
        if "opensooq" in sources: adapters.append(OpenSooqAdapter())
        if "instagram" in sources: adapters.append(InstagramAdapter())
        if "yallamotor" in sources: adapters.append(YallaMotorAdapter())
        if "dubizzle" in sources: adapters.append(DubizzleAdapter())
        if "carsbh" in sources: adapters.append(CarsbhAdapter())
        if "righcars" in sources: adapters.append(RighCarsAdapter())
        if "facebook" in sources: adapters.append(FacebookAdapter())
        if "mock" in sources: adapters.append(MockAdapter())

        if not adapters:
            print("No adapters selected!")
            return

        session_seen = set()

        try:
            async for db in get_db():
                while True:
                    yielded = False
                    
                    # Fire status events for all adapters
                    for adapter in adapters:
                        adapter_name = adapter.__class__.__name__.replace("Adapter", "").lower()
                        yield ServerSentEvent(
                            data=json.dumps({"adapter": adapter_name, "state": "scanning"}),
                            event="status"
                        )
                        
                    # Wrapper to fetch all listings from an adapter concurrently
                    async def fetch_adapter_data(adapter):
                        adapter_name = adapter.__class__.__name__.replace("Adapter", "").lower()
                        results = []
                        try:
                            async for item in adapter.fetch_listings():
                                results.append(item)
                        except Exception as e:
                            print(f"[{adapter_name}] Fetch Error: {e}")
                        return adapter_name, results

                    tasks = [fetch_adapter_data(adapter) for adapter in adapters]
                    
                    # Process whichever adapter finishes first
                    for coro in asyncio.as_completed(tasks):
                        adapter_name, raw_listings = await coro
                        
                        if not raw_listings:
                            yield ServerSentEvent(
                                data=json.dumps({"adapter": adapter_name, "state": "idle"}),
                                event="status"
                            )
                            continue

                        # Concurrent Scoring & AI Analysis
                        async def process_listing(raw_listing):
                            try:
                                fp = f"{raw_listing.source}_{raw_listing.source_id}"
                                fp_hash = hashlib.md5(fp.encode()).hexdigest()
                                if fp_hash in session_seen:
                                    return None

                                scored_deal = await self.scorer.score_deal(raw_listing, db)
                                if not scored_deal or scored_deal.total_score < 0:
                                    return None
                                    
                                scored_deal.fingerprint_hash = fp_hash
                                
                                # DB Read for existing insights
                                async with db.execute(
                                    "SELECT id, ai_insights FROM deals WHERE fingerprint_hash = ?",
                                    (fp_hash,)
                                ) as cursor:
                                    existing = await cursor.fetchone()
                                    
                                if existing and existing["ai_insights"]:
                                    scored_deal.ai_insights = existing["ai_insights"]
                                    scored_deal.is_gemini_analyzed = not existing["ai_insights"].startswith("AI Analysis ")
                                elif scored_deal.total_score >= 0:
                                    ai_insight = await self.ai.analyze_deal(scored_deal)
                                    scored_deal.ai_insights = ai_insight
                                    scored_deal.is_gemini_analyzed = not ai_insight.startswith("AI Analysis ")

                                # Absolute Image URL fix
                                if scored_deal.listing.image_url:
                                    img_url = scored_deal.listing.image_url
                                    if img_url.startswith("//"):
                                        img_url = "https:" + img_url
                                    elif img_url.startswith("/"):
                                        if "opensooq" in scored_deal.listing.source:
                                            img_url = "https://opensooq-imagesv2.os-cdn.com" + img_url
                                        elif "yallamotor" in scored_deal.listing.source:
                                            img_url = "https://bh.yallamotor.com" + img_url
                                        elif "dubizzle" in scored_deal.listing.source:
                                            img_url = "https://www.dubizzle.com.bh" + img_url
                                        elif "carsbh" in scored_deal.listing.source:
                                            img_url = "https://carsbh.com" + img_url
                                        elif "righcars" in scored_deal.listing.source:
                                            img_url = "https://righcars.com" + img_url
                                    scored_deal.listing.image_url = img_url
                                    
                                return scored_deal
                            except Exception as e:
                                print(f"Processing error for {raw_listing.title}: {e}")
                                return None

                        # Process the batch concurrently but yield as soon as each deal is scored!
                        scoring_tasks = [process_listing(raw) for raw in raw_listings]
                        
                        for scoring_coro in asyncio.as_completed(scoring_tasks):
                            sd = await scoring_coro
                            if sd and sd.fingerprint_hash not in session_seen:
                                session_seen.add(sd.fingerprint_hash)
                                
                                # Sequential DB Insert
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
                                        ai_insights=COALESCE(excluded.ai_insights, deals.ai_insights),
                                        image_url=COALESCE(excluded.image_url, deals.image_url)
                                    """,
                                    (
                                        sd.fingerprint_hash, sd.listing.source, sd.listing.source_id,
                                        sd.listing.title, sd.listing.make, sd.listing.model, sd.listing.year,
                                        sd.listing.price_bhd, sd.listing.mileage_km, sd.listing.phone,
                                        sd.listing.url, sd.listing.description, sd.listing.image_url,
                                        sd.total_score, sd.net_profit, sd.ai_insights,
                                    ),
                                )
                                await db.commit()

                                print(f"Yield deal source={sd.listing.source} score={sd.total_score:.1f} {sd.listing.year} {sd.listing.make} {sd.listing.model} @ {sd.listing.price_bhd} BHD")
                                
                                yield ServerSentEvent(
                                    data=json.dumps(sd.dict(), default=str),
                                    event="new_deal",
                                )
                                yielded = True
                            
                        # Adapter cycle finished
                        yield ServerSentEvent(
                            data=json.dumps({"adapter": adapter_name, "state": "idle"}),
                            event="status"
                        )
                        
                    if not yielded:
                        yield ServerSentEvent(data="keep-alive", event="ping")
                        
                    # Wait slightly before restarting the full concurrent loop
                    await asyncio.sleep(random.uniform(8, 15))
                        
        except asyncio.CancelledError:
            print("Client disconnected from scan stream.")
