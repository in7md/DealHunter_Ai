import aiosqlite
from typing import AsyncGenerator

DATABASE_URL = "dealhunter.db"

async def init_db():
    async with aiosqlite.connect(DATABASE_URL) as db:
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute('''
            CREATE TABLE IF NOT EXISTS deals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fingerprint_hash TEXT UNIQUE NOT NULL,
                source TEXT,
                source_id TEXT,
                title TEXT,
                make TEXT,
                model TEXT,
                year INTEGER,
                price_bhd REAL,
                mileage_km REAL,
                phone TEXT,
                url TEXT,
                description TEXT,
                image_url TEXT,
                total_score REAL,
                net_profit REAL,
                ai_insights TEXT,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        try:
            await db.execute('ALTER TABLE deals ADD COLUMN image_url TEXT')
        except Exception:
            pass # column already exists
        await db.commit()

async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    async with aiosqlite.connect(DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        yield db
