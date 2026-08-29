import asyncio
import httpx
import json
import random
from typing import AsyncGenerator, Optional
from app.database.models import RawListing
from app.adapters.base import BaseAdapter
from app.core.ai_analyzer import AIAnalyzer

INSTAGRAM_ACCOUNTS = [
    "carsbahrain_at", "carsstore", "showroom_bh", "bahraincars.co", "carsbh911", 
    "carsbh1", "bahrain_cars86", "carssale_bh", "special_cars_bh", "bahraincarsm", 
    "yaad_cars", "bahrain_1car", "moatrik_bh", "car_bh117", "ba7raincars7", 
    "al3mad_cars", "bh_numbers", "bahraincarsx", "burashed_car", "sayartiii", 
    "sa.cars.bh", "driv.bh", "bahrain_auctions907_", "bhcar_911", "916cars.bh", 
    "miamicars.bh", "miamicars.bh1", "hamadcars.bh", "ba7raini.cars", 
    "bahrain_cars_market", "cars_in_bahrain"
]

class InstagramAdapter(BaseAdapter):
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "X-IG-App-ID": "936619743392459",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
        }
        self.ai = AIAnalyzer()
        self.current_idx = 0

    async def fetch_listings(self) -> AsyncGenerator[RawListing, None]:
        if not INSTAGRAM_ACCOUNTS: return
        account = INSTAGRAM_ACCOUNTS[self.current_idx]
        self.current_idx = (self.current_idx + 1) % len(INSTAGRAM_ACCOUNTS)
        
        import time
        try:
            async with httpx.AsyncClient(headers=self.headers, follow_redirects=True, timeout=5.0) as client:
                url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={account}&_t={int(time.time())}"
                response = await client.get(url)
                
                if response.status_code == 429 or response.status_code == 403:
                    print(f"Instagram blocked (status {response.status_code}).")
                    return
                    
                if response.status_code != 200:
                    return
                    
                data = response.json()
                user = data.get("data", {}).get("user", {})
                if not user:
                    return
                    
                edges = user.get("edge_owner_to_timeline_media", {}).get("edges", [])
                
                # Process top 2 posts
                for edge in edges[:2]:
                    node = edge.get("node", {})
                    shortcode = node.get("shortcode")
                    display_url = node.get("display_url")
                    caption_edges = node.get("edge_media_to_caption", {}).get("edges", [])
                    
                    if not caption_edges:
                        continue
                        
                    caption = caption_edges[0].get("node", {}).get("text", "")
                    
                    if not caption or len(caption) < 20:
                        continue
                        
                    # Attempt AI parsing
                    make = None
                    model = None
                    year = None
                    price = None
                    mileage = None
                    try:
                        details = await self.ai.extract_car_details(caption)
                        if details:
                            make = details.get("make")
                            model = details.get("model")
                            if details.get("year"): year = int(details.get("year"))
                            if details.get("price"): price = float(details.get("price"))
                            if details.get("mileage"): mileage = float(details.get("mileage"))
                    except Exception:
                        pass
                        
                    if not price:
                        price_match = re.search(r'(?:BHD|BD)\s*(\d[\d,]*)', caption, re.IGNORECASE)
                        if not price_match:
                            price_match = re.search(r'(\d[\d,]*)\s*(?:BHD|BD)', caption, re.IGNORECASE)
                        if price_match:
                            price = float(price_match.group(1).replace(',', ''))
                            
                    if not year:
                        year_match = re.search(r'\b(199[0-9]|20[0-2][0-9])\b', caption)
                        if year_match:
                            year = int(year_match.group(1))

                    if not make or make == "Unknown" or not model or model == "Unknown":
                        from app.core.text_parser import extract_make_model_fallback
                        make, model = extract_make_model_fallback(caption)
                        
                    if not price or not year or not make or make == "Unknown" or not model or model == "Unknown":
                        continue

                    yield RawListing(
                        source="instagram",
                        source_id=shortcode,
                        title=f"{year} {make} {model}",
                        make=make,
                        model=model,
                        year=year,
                        price_bhd=price,
                        mileage_km=mileage,
                        phone=None,
                        url=f"https://instagram.com/p/{shortcode}",
                        description=f"Account: @{account} - {caption[:100]}...",
                        image_url=display_url
                    )
        except (httpx.TimeoutException, httpx.RequestError) as e:
            print(f"Instagram Network Timeout/Error on {account}: {e}")
        except Exception as e:
            print(f"Instagram Adapter Error on {account}: {e}")
