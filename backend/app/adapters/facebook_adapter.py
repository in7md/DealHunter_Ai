from typing import AsyncGenerator
from app.adapters.base import BaseAdapter
from app.database.models import RawListing
from app.core.ai_analyzer import AIAnalyzer
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import asyncio
import re

class FacebookAdapter(BaseAdapter):
    def __init__(self):
        self.url = "https://www.facebook.com/marketplace/manama/vehicles/"
        self.ai = AIAnalyzer()
        
    async def fetch_listings(self) -> AsyncGenerator[RawListing, None]:
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                    viewport={"width": 1280, "height": 720},
                    locale="en-US"
                )
                
                # Block image requests and CSS to speed up loading and save bandwidth
                await context.route("**/*", lambda route: route.continue_() if route.request.resource_type in ["document", "script", "xhr", "fetch"] else route.abort())

                page = await context.new_page()
                try:
                    await page.goto(self.url, wait_until="domcontentloaded", timeout=5000)
                    
                    # Scroll down to load some items
                    for _ in range(3):
                        await page.evaluate("window.scrollBy(0, 1000)")
                        await asyncio.sleep(1)

                    # Check for login wall
                    login_indicators = await page.locator("text=Log In").count()
                    if login_indicators > 2:
                        print("FB Login Wall hit, skipping...")
                        await browser.close()
                        return

                    # Extract listings
                    items = await page.evaluate("""() => {
                        const links = Array.from(document.querySelectorAll('a[href*="/marketplace/item/"]'));
                        const results = [];
                        const seen = new Set();
                        
                        links.forEach(link => {
                            const href = link.href;
                            if(seen.has(href)) return;
                            seen.add(href);
                            
                            const textContent = link.innerText;
                            const img = link.querySelector('img');
                            const imgUrl = img ? img.src : null;
                            
                            if(textContent && imgUrl) {
                                results.push({
                                    url: href,
                                    text: textContent,
                                    img: imgUrl
                                });
                            }
                        });
                        return results;
                    }""")
                    
                    if not items:
                        print("Facebook Adapter: No items found or blocked.")
                        await browser.close()
                        return

                    # Process top 5 items per cycle to avoid Gemini rate limits
                    for item in items[:5]:
                        try:
                            url = item["url"]
                            raw_text = item["text"].replace("\n", " ")
                            img_url = item["img"]
                            
                            item_id = url.split("/item/")[1].split("/")[0] if "/item/" in url else url
                            
                            # Initial fast regex for price to save AI tokens if obvious
                            price = None
                            price_match = re.search(r'(?:BHD|BD)\s*(\d[\d,]*)', raw_text, re.IGNORECASE)
                            if not price_match:
                                price_match = re.search(r'(\d[\d,]*)\s*(?:BHD|BD)', raw_text, re.IGNORECASE)
                            if price_match:
                                price = float(price_match.group(1).replace(',', ''))
                                
                            make = None
                            model = None
                            year = None
                            
                            year_match = re.search(r'\b(199[0-9]|20[0-2][0-9])\b', raw_text)
                            if year_match:
                                year = int(year_match.group(1))

                            try:
                                # Let Gemini parse it if messy
                                details = await self.ai.extract_car_details(raw_text)
                                if details:
                                    make = details.get("make")
                                    model = details.get("model")
                                    if details.get("year"): year = int(details.get("year"))
                                    if details.get("price"): price = float(details.get("price"))
                            except Exception:
                                pass
                                
                            # Deterministic Fallback if AI failed or make/model is missing/Unknown
                            if not make or make == "Unknown" or not model or model == "Unknown":
                                from app.core.text_parser import extract_make_model_fallback
                                make, model = extract_make_model_fallback(raw_text)

                            if not make or not model or make == "Unknown" or model == "Unknown" or not price or not year:
                                continue

                            yield RawListing(
                                source="facebook",
                                source_id=item_id,
                                title=f"{year} {make} {model}",
                                make=make,
                                model=model,
                                year=year,
                                price_bhd=price,
                                mileage_km=float(details.get("mileage")) if details.get("mileage") else None,
                                phone=None,
                                url=url,
                                description=raw_text[:200],
                                image_url=img_url
                            )
                        except Exception as e:
                            continue
                except PlaywrightTimeoutError:
                    print("Facebook Adapter: Page load timeout.")
                finally:
                    await browser.close()
        except Exception as e:
            print(f"Facebook Adapter Error: {e}")
