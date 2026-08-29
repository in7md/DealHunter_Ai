import asyncio
from app.adapters.opensooq_adapter import OpenSooqAdapter

async def test_scraper():
    adapter = OpenSooqAdapter()
    print("Testing OpenSooq Adapter...")
    count = 0
    async for listing in adapter.fetch_listings():
        print(f"Found listing: {listing.title} - {listing.price_bhd} BHD")
        count += 1
        if count >= 5:
            break
    print(f"Total found: {count}")

if __name__ == "__main__":
    asyncio.run(test_scraper())
