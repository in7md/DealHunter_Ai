import asyncio
import httpx
import re
import random
import json
from bs4 import BeautifulSoup
from typing import AsyncGenerator, Optional
from app.database.models import RawListing
from app.adapters.base import BaseAdapter

MAKE_ALIASES = {
    "تويوتا": "Toyota",
    "toyota": "Toyota",
    "لكزس": "Lexus",
    "lexus": "Lexus",
    "نيسان": "Nissan",
    "nissan": "Nissan",
    "هوندا": "Honda",
    "honda": "Honda",
    "هونداي": "Hyundai",
    "هيونداي": "Hyundai",
    "hyundai": "Hyundai",
    "كيا": "Kia",
    "kia": "Kia",
    "مرسيدس": "Mercedes",
    "mercedes": "Mercedes",
    "mercedes-benz": "Mercedes",
    "بي ام دبليو": "BMW",
    "بي إم دبليو": "BMW",
    "bmw": "BMW",
    "جاكوار": "Jaguar",
    "jaguar": "Jaguar",
    "شفروليه": "Chevrolet",
    "chevrolet": "Chevrolet",
    "فورد": "Ford",
    "ford": "Ford",
    "جيب": "Jeep",
    "jeep": "Jeep",
    "جي ام سي": "GMC",
    "gmc": "GMC",
    "لاند روفر": "Land Rover",
    "land rover": "Land Rover",
    "رنج روفر": "Land Rover",
    "أودي": "Audi",
    "audi": "Audi",
    "بورش": "Porsche",
    "porsche": "Porsche",
    "مازدا": "Mazda",
    "mazda": "Mazda",
    "ميتسوبيشي": "Mitsubishi",
    "mitsubishi": "Mitsubishi",
    "سوزوكي": "Suzuki",
    "suzuki": "Suzuki",
    "فولكس واجن": "Volkswagen",
    "volkswagen": "Volkswagen",
    "إنفينيتي": "Infiniti",
    "infiniti": "Infiniti",
    "كاديلاك": "Cadillac",
    "cadillac": "Cadillac",
    "دودج": "Dodge",
    "dodge": "Dodge",
}


class OpenSooqAdapter(BaseAdapter):
    def __init__(self):
        self.base_url = "https://bh.opensooq.com"
        self.start_url = f"{self.base_url}/ar/cars/cars-for-sale"
        self.images_cdn = "https://opensooq-imagesv2.os-cdn.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "ar,en;q=0.9",
            "Referer": "https://bh.opensooq.com/",
        }
        self.page = 1

    def _normalize_make(self, raw: str) -> str:
        key = (raw or "").strip().lower()
        if key in MAKE_ALIASES:
            return MAKE_ALIASES[key]
        return (raw or "Unknown").strip() or "Unknown"

    def _parse_year(self, item: dict) -> int:
        for cp in item.get("starCps") or []:
            icon = cp.get("icon") or ""
            label = str(cp.get("label") or "")
            if "year.webp" in icon:
                digits = re.sub(r"[^\d]", "", label)
                if len(digits) >= 4:
                    return int(digits[:4])
        for text in (item.get("title"), item.get("subtitle"), item.get("highlights")):
            if not text:
                continue
            match = re.search(r"\b(19\d{2}|20\d{2})\b", str(text).replace(",", ""))
            if match:
                return int(match.group(1))
        return 2000

    def _parse_make_model(self, item: dict) -> tuple[str, str]:
        specs: list[str] = []
        for cp in item.get("starCps") or []:
            icon = cp.get("icon") or ""
            label = (cp.get("label") or "").strip()
            if "make_mode_trim" in icon and label:
                specs.append(label)
        if specs:
            make = self._normalize_make(specs[0])
            model = " ".join(specs[1:3]).strip() or "Unknown"
            return make, model

        cps = [str(x).strip() for x in (item.get("cps") or []) if str(x).strip()]
        # Typical: [condition, make, model, trim, year, km, body]
        if len(cps) >= 3:
            return self._normalize_make(cps[1]), cps[2]

        title = item.get("title") or ""
        from app.core.text_parser import extract_make_model_fallback
        make, model = extract_make_model_fallback(title)
        return make or "Unknown", model or "Unknown"

    def _parse_price(self, item: dict) -> float:
        price_text = str(item.get("price_amount") or "").strip()
        if not price_text or "اتصل" in price_text or "call" in price_text.lower():
            return 0.0
        
        # Convert Eastern Arabic digits to Western digits
        eastern_to_western = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
        price_text = price_text.translate(eastern_to_western)

        # Match numbers with commas and optional decimals
        match = re.search(r"(\d[\d,]*(?:\.\d+)?)", price_text)
        if not match:
            return 0.0
        try:
            val = float(match.group(1).replace(",", ""))
            return val if val > 0 else 0.0
        except (ValueError, TypeError):
            return 0.0

    def _image_url(self, item: dict) -> Optional[str]:
        uri = item.get("image_uri")
        if not uri:
            return None
        if str(uri).startswith("http"):
            return str(uri)
        return f"{self.images_cdn}/previews/400x0/{uri}"

    def _listing_url(self, item: dict) -> str:
        full_url = item.get("post_url") or ""
        if full_url and not str(full_url).startswith("http"):
            return f"{self.base_url}{full_url}"
        if full_url:
            return str(full_url)
        listing_id = item.get("id")
        if listing_id:
            return f"{self.base_url}/ar/post/{listing_id}"
        return self.start_url

    def _description(self, item: dict) -> str:
        parts = [
            item.get("masked_description") or "",
            f"الموقع: {item.get('city_label', 'البحرين')} {item.get('nhood_label', '')}".strip(),
        ]
        spec_labels = [str(cp.get("label")) for cp in (item.get("starCps") or []) if cp.get("label")]
        if spec_labels:
            parts.append(" | ".join(spec_labels))
        return " — ".join(p for p in parts if p).strip()

    def _to_listing(self, item: dict) -> Optional[RawListing]:
        price_val = self._parse_price(item)
        if price_val <= 0:
            return None

        make, model = self._parse_make_model(item)
        if make == "Unknown" or model == "Unknown":
            return None
            
        year = self._parse_year(item)

        mileage = item.get("kilometers_Cars_value_i")
        try:
            mileage_km = float(str(mileage).replace(",", "")) if mileage else None
        except (TypeError, ValueError):
            mileage_km = None

        source_id = str(item.get("id", ""))
        if not source_id:
            return None

        return RawListing(
            source="opensooq",
            source_id=source_id,
            title=item.get("title") or f"{year} {make} {model}",
            make=make,
            model=model,
            year=year,
            price_bhd=price_val,
            mileage_km=mileage_km,
            phone=item.get("phone_number"),
            url=self._listing_url(item),
            description=self._description(item),
            image_url=self._image_url(item),
        )

    async def fetch_listings(self) -> AsyncGenerator[RawListing, None]:
        import time
        url = f"{self.start_url}?page={self.page}&_t={int(time.time())}"
        
        # Advance page for next time
        self.page += 1
        if self.page > 50:
            self.page = 1

        try:
            async with httpx.AsyncClient(headers=self.headers, follow_redirects=True, timeout=5.0) as client:
                response = await client.get(url)
                if response.status_code != 200:
                    return

                soup = BeautifulSoup(response.text, "html.parser")
                script = soup.find("script", id="__NEXT_DATA__")
                if not script or not script.string:
                    return

                data = json.loads(script.string)
                try:
                    listings_data = data["props"]["pageProps"]["serpApiResponse"]["listings"]
                    items = listings_data.get("items", []) if isinstance(listings_data, dict) else listings_data
                except (KeyError, TypeError):
                    return

                if not items:
                    self.page = 1
                    return

                for item in items:
                    listing = self._to_listing(item)
                    if listing:
                        yield listing
        except (httpx.TimeoutException, httpx.RequestError) as e:
            print(f"OpenSooq Network Timeout/Error: {e}")
        except Exception as e:
            import traceback
            print(f"OpenSooq Adapter Error: {e}")
