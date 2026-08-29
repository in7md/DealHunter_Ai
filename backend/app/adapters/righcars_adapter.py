import asyncio
import httpx
from bs4 import BeautifulSoup
from typing import AsyncGenerator
import re
from app.database.models import RawListing
from app.adapters.base import BaseAdapter
from app.core.text_parser import extract_make_model_fallback

class RighCarsAdapter(BaseAdapter):
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        self.page = 1

    async def fetch_listings(self) -> AsyncGenerator[RawListing, None]:
        import time
        url = f"https://righcars.com?page={self.page}&_t={int(time.time())}"
        
        self.page += 1
        if self.page > 50: self.page = 1

        try:
            async with httpx.AsyncClient(headers=self.headers, follow_redirects=True, timeout=5.0) as client:
                response = await client.get(url)
                if response.status_code != 200:
                    return

                soup = BeautifulSoup(response.text, "html.parser")
                items = soup.find_all("div", class_=lambda c: c and ("car" in c.lower() or "post" in c.lower() or "card" in c.lower()))
                
                valid_items = [i for i in items if i.find("a") and i.find("img")]
                
                if not valid_items:
                    self.page = 1
                    return
                
                for item in valid_items[:15]:
                    link_el = item.find("a")
                    if not link_el: continue
                    
                    href = link_el.get("href", "")
                    full_url = f"https://righcars.com{href}" if href.startswith("/") else href
                    
                    title = link_el.get_text(strip=True) or (item.find("h2") and item.find("h2").get_text(strip=True))
                    if not title or len(title) < 4: continue
                    
                    text_content = item.get_text(separator=" ", strip=True)
                    price_match = re.search(r'(\d[\d,]*)\s*(BHD|BD|دينار|بحريني)', text_content, re.IGNORECASE)
                    if not price_match:
                        continue
                    price = float(price_match.group(1).replace(",", ""))
                    if price <= 0: continue
                    
                    year = 2015
                    year_match = re.search(r'\b(199[0-9]|20[0-2][0-9])\b', title)
                    if year_match:
                        year = int(year_match.group(1))

                    make, model = extract_make_model_fallback(title)
                    if not make or not model:
                        continue

                    img_el = item.find("img")
                    img_url = img_el.get("src") if img_el else None
                    if img_url and not img_url.startswith("http"):
                        img_url = f"https://righcars.com{img_url}" if img_url.startswith("/") else f"https://righcars.com/{img_url}"

                    yield RawListing(
                        source="righcars",
                        source_id=full_url.split("/")[-1] or title,
                        title=title,
                        make=make,
                        model=model,
                        year=year,
                        price_bhd=price,
                        mileage_km=None,
                        phone=None,
                        url=full_url,
                        description=title,
                        image_url=img_url
                    )
        except (httpx.TimeoutException, httpx.RequestError) as e:
            print(f"RighCars Network Timeout/Error: {e}")
        except Exception as e:
            print(f"RighCars Adapter Error: {e}")
