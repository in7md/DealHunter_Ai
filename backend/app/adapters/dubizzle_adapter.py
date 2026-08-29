import asyncio
import httpx
from bs4 import BeautifulSoup
from typing import AsyncGenerator
from app.database.models import RawListing
from app.adapters.base import BaseAdapter
from app.core.text_parser import extract_make_model_fallback

class DubizzleAdapter(BaseAdapter):
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }
        self.page = 1

    async def fetch_listings(self) -> AsyncGenerator[RawListing, None]:
        import time
        url = f"https://www.dubizzle.com.bh/en/vehicles/cars/?page={self.page}&_t={int(time.time())}"
        
        self.page += 1
        if self.page > 50: self.page = 1

        try:
            async with httpx.AsyncClient(headers=self.headers, follow_redirects=True, timeout=5.0) as client:
                response = await client.get(url)
                if response.status_code != 200:
                    return

                soup = BeautifulSoup(response.text, "html.parser")
                
                # Extract via NEXT_DATA or generic extraction
                script = soup.find("script", id="__NEXT_DATA__")
                if script and script.string:
                    import json
                    try:
                        data = json.loads(script.string)
                    except Exception:
                        pass

                # Robust fallback: Scrape standard article/div tags
                listings = soup.find_all("div", attrs={"aria-label": "Listing"})
                if not listings:
                    listings = soup.find_all("article")
                    
                if not listings:
                    self.page = 1
                    return

                for item in listings[:15]:
                    try:
                        price_text = item.find(string=lambda t: t and "BHD" in t)
                        if not price_text:
                            continue
                            
                        price = float(''.join(filter(str.isdigit, price_text)))
                        if price <= 0:
                            continue

                        title_el = item.find("h2") or item.find("div", class_=lambda c: c and "title" in c.lower())
                        if not title_el:
                            continue
                        title = title_el.get_text(strip=True)

                        year = 2015 
                        import re
                        year_match = re.search(r'\b(199[0-9]|20[0-2][0-9])\b', title)
                        if year_match:
                            year = int(year_match.group(1))

                        make, model = extract_make_model_fallback(title)
                        if not make or not model:
                            continue

                        link_el = item.find("a")
                        url_suffix = link_el["href"] if link_el else ""
                        full_url = f"https://www.dubizzle.com.bh{url_suffix}" if url_suffix.startswith("/") else url_suffix

                        img_el = item.find("img")
                        img_url = img_el["src"] if img_el else None
                        if img_url:
                            if img_url.startswith("//"):
                                img_url = "https:" + img_url
                            elif img_url.startswith("/"):
                                img_url = "https://www.dubizzle.com.bh" + img_url

                        yield RawListing(
                            source="dubizzle",
                            source_id=full_url.split("-")[-1].replace("/", "") or title,
                            title=title,
                            make=make,
                            model=model,
                            year=year,
                            price_bhd=price,
                            mileage_km=None,
                            phone=None,
                            url=full_url or url,
                            description=title,
                            image_url=img_url
                        )
                    except Exception as e:
                        continue
        except (httpx.TimeoutException, httpx.RequestError) as e:
            print(f"Dubizzle Network Timeout/Error: {e}")
        except Exception as e:
            print(f"Dubizzle Adapter Error: {e}")
