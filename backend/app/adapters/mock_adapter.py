import asyncio
import random
from typing import AsyncGenerator
from app.database.models import RawListing
from app.adapters.base import BaseAdapter

class MockAdapter(BaseAdapter):
    async def fetch_listings(self) -> AsyncGenerator[RawListing, None]:
        cars = [
            {"make": "Toyota", "model": "Camry", "year": 2021, "price_bhd": 4200, "desc": "وكالة البحرين، صبغ وكالة، بيمة وفحص سنة، سرفس الوكالة", "km": 68000},
            {"make": "Lexus", "model": "IS350", "year": 2018, "price_bhd": 6200, "desc": "وارد أمريكا، أوراق جمارك، شاشة كبيرة، نظام ملاحة", "km": 110000},
            {"make": "Nissan", "model": "Patrol", "year": 2020, "price_bhd": 9800, "desc": "وكالة البحرين، المكينة الكبيرة 400 حصان، مالك أول، نظيف جداً", "km": 90000},
            {"make": "Honda", "model": "Accord", "year": 2019, "price_bhd": 2800, "desc": "بيمة وفحص جديد، صيانة دورية، تواير جديدة، السعر قابل للتفاوض للجادين", "km": 80000},
            {"make": "Toyota", "model": "Land Cruiser", "year": 2015, "price_bhd": 8900, "desc": "للبيع المستعجل لدواعي السفر، قاطع 150 ألف كيلو، شرط الفحص", "km": 150000},
            {"make": "BMW", "model": "5 Series", "year": 2017, "price_bhd": 5100, "desc": "فل أوبشن، خالي من الحوادث، صبغ الوكالة بالكامل، M-Kit", "km": 140000},
        ]

        for i in range(10000):
            await asyncio.sleep(1.2)
            base_car = random.choice(cars)
            # Keep a few listings clearly under market so high scores appear
            jitter = 0.92 if i % 7 == 0 else random.uniform(0.95, 1.12)
            price = round(base_car["price_bhd"] * jitter, 0)

            yield RawListing(
                source="opensooq_mock",
                source_id=f"mock_{i}",
                title=f"{base_car['year']} {base_car['make']} {base_car['model']} للبيع",
                make=base_car["make"],
                model=base_car["model"],
                year=base_car["year"],
                price_bhd=price,
                mileage_km=base_car["km"] * random.uniform(0.85, 1.15),
                phone=f"+9733{random.randint(1000000, 9999999)}",
                url=f"https://bh.opensooq.com/ar/post/mock-{i}",
                description=base_car["desc"],
                image_url=f"https://picsum.photos/seed/dealhunter{i}/400/300",
            )
