import aiosqlite
import json
from datetime import datetime

DB_PATH = "jobhunter.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS resume (
                id INTEGER PRIMARY KEY,
                filename TEXT,
                content TEXT,
                parsed_data TEXT,
                uploaded_at TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                title TEXT,
                company TEXT,
                location TEXT,
                city TEXT,
                platform TEXT,
                url TEXT,
                description TEXT,
                salary TEXT,
                posted_date TEXT,
                match_score REAL,
                cover_letter TEXT,
                status TEXT DEFAULT 'pending_review',
                fetched_at TEXT,
                applied_at TEXT,
                rejection_reason TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT,
                applied_at TEXT,
                email_sent INTEGER DEFAULT 0,
                email_to TEXT,
                status TEXT DEFAULT 'applied',
                notes TEXT,
                FOREIGN KEY (job_id) REFERENCES jobs(id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        # Insert defaults if not exist
        defaults = [
            ("email_address", ""),
            ("email_password", ""),
            ("anthropic_api_key", ""),
            ("max_job_age_days", "7"),
            ("city_salary_ranges", json.dumps({})),
            ("selected_cities", json.dumps(["Dubai", "Sharjah", "Ajman", "Abu Dhabi"])),
            ("selected_platforms", json.dumps(["linkedin", "indeed", "bayt", "naukrigulf"])),
            ("auto_apply_enabled", "false"),
            ("linkedin_email", ""),
            ("linkedin_password", ""),
            ("indeed_email", ""),
            ("indeed_password", ""),
        ]
        for key, value in defaults:
            await db.execute(
                "INSERT OR IGNORE INTO app_settings (key, value) VALUES (?, ?)",
                (key, value)
            )
        await db.commit()

async def get_setting(key: str) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM app_settings WHERE key=?", (key,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else ""

async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)",
            (key, value)
        )
        await db.commit()

async def get_db():
    return aiosqlite.connect(DB_PATH)
