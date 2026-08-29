import asyncio
import httpx
import json
from bs4 import BeautifulSoup

async def dump_json():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    }
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        response = await client.get("https://bh.opensooq.com/ar/cars/cars-for-sale")
        soup = BeautifulSoup(response.text, 'html.parser')
        script = soup.find('script', id='__NEXT_DATA__')
        if script:
            with open("opensooq.json", "w", encoding="utf-8") as f:
                json.dump(json.loads(script.string), f, ensure_ascii=False, indent=2)
            print("Dumped to opensooq.json")

if __name__ == "__main__":
    asyncio.run(dump_json())
