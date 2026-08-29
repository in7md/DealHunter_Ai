import asyncio
import httpx
from bs4 import BeautifulSoup
from typing import AsyncGenerator
import re
from app.database.models import RawListing
from app.adapters.base import BaseAdapter
from app.core.text_parser import extract_make_model_fallback

class YallaMotorAdapter(BaseAdapter):
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        self.page = 1

    async def fetch_listings(self) -> AsyncGenerator[RawListing, None]:
        import time
        url = f"https://bh.yallamotor.com/used-cars?page={self.page}&_t={int(time.time())}"
        
        self.page += 1
        if self.page > 50: self.page = 1

        try:
            async with httpx.AsyncClient(headers=self.headers, follow_redirects=True, timeout=5.0) as client:
                response = await client.get(url)
                if response.status_code != 200:
                    return

                soup = BeautifulSoup(response.text, "html.parser")
                items = soup.find_all("div", class_="m32-single-result")
                
                if not items:
                    self.page = 1
                    return
                
                for item in items[:15]:
                    try:
                        title_el = item.find("h2")
                        if not title_el:
                            continue
                        
                        title = title_el.get_text(strip=True)
                        link_el = title_el.find("a")
                        href = link_el["href"] if link_el else ""
                        full_url = f"https://bh.yallamotor.com{href}" if href.startswith("/") else href
                        
                        price_el = item.find("span", class_="price")
                        if not price_el:
                            continue
                        
                        price_text = price_el.get_text(strip=True)
                        price_match = re.search(r'(\d[\d,]*)', price_text)
                        if not price_match:
                            continue
                        price = float(price_match.group(1).replace(",", ""))
                        
                        year = 2015
                        year_match = re.search(r'\b(199[0-9]|20[0-2][0-9])\b', title)
                        if year_match:
                            year = int(year_match.group(1))

                        make, model = extract_make_model_fallback(title)
                        if not make or not model:
                            continue

                        img_el = item.find("img")
                        img_url = img_el.get("data-src") or img_el.get("src") if img_el else None
                        if img_url:
                            if img_url.startswith("//"):
                                img_url = "https:" + img_url
                            elif img_url.startswith("/"):
                                img_url = "https://bh.yallamotor.com" + img_url

                        yield RawListing(
                            source="yallamotor",
                            source_id=full_url.split("/")[-1] or title,
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
            print(f"YallaMotor Network Timeout/Error: {e}")
        except Exception as e:
            print(f"YallaMotor Adapter Error: {e}")
