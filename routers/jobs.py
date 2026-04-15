from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
import json
import aiosqlite
from datetime import datetime
from database import get_setting, DB_PATH
from services.job_scraper import search_all_platforms
from services.ai_service import score_and_enrich_jobs, generate_cover_letter

router = APIRouter()

class SearchRequest(BaseModel):
    force_refresh: bool = False

class UpdateCoverLetter(BaseModel):
    cover_letter: str

class RejectJob(BaseModel):
    reason: Optional[str] = ""

@router.post("/search")
async def search_jobs(req: SearchRequest, background_tasks: BackgroundTasks):
    """Trigger a new job search based on resume and settings"""
    api_key = await get_setting("anthropic_api_key")
    if not api_key:
        raise HTTPException(400, "Anthropic API key not configured")
    
    # Get resume
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT parsed_data FROM resume ORDER BY id DESC LIMIT 1") as cursor:
            row = await cursor.fetchone()
            if not row:
                raise HTTPException(400, "No resume uploaded. Please upload your resume first.")
            resume_data = json.loads(row[0])
    
    # Get settings
    cities = json.loads(await get_setting("selected_cities") or '["Dubai"]')
    platforms = json.loads(await get_setting("selected_platforms") or '["linkedin","indeed","bayt","naukrigulf"]')
    max_age = int(await get_setting("max_job_age_days") or "7")
    
    suitable_roles = resume_data.get("suitable_roles", [resume_data.get("title", "Digital Marketing")])
    
    # Search all platforms
    raw_jobs = await search_all_platforms(suitable_roles, cities, platforms, max_age)
    
    if not raw_jobs:
        return {"jobs_found": 0, "message": "No jobs found. Try adjusting search settings or check your internet connection."}
    
    # Score and enrich with AI
    enriched_jobs = await score_and_enrich_jobs(raw_jobs, resume_data, api_key)
    
    # Save to DB
    saved = 0
    async with aiosqlite.connect(DB_PATH) as db:
        for job in enriched_jobs:
            try:
                await db.execute("""
                    INSERT OR REPLACE INTO jobs 
                    (id, title, company, location, city, platform, url, description, salary, 
                     posted_date, match_score, cover_letter, status, fetched_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    job["id"], job.get("title"), job.get("company"), job.get("location"),
                    job.get("city"), job.get("platform"), job.get("url"), job.get("description",""),
                    job.get("salary",""), job.get("posted_date"), job.get("match_score",0),
                    job.get("cover_letter",""), "pending_review", datetime.now().isoformat()
                ))
                saved += 1
            except Exception as e:
                print(f"Error saving job: {e}")
        await db.commit()
    
    return {"jobs_found": saved, "message": f"Found {saved} jobs. Review them in the approval queue."}

@router.get("/pending")
async def get_pending_jobs():
    """Get jobs waiting for approval"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM jobs WHERE status = 'pending_review' 
            ORDER BY match_score DESC
        """) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

@router.get("/all")
async def get_all_jobs(status: Optional[str] = None, platform: Optional[str] = None, city: Optional[str] = None):
    """Get all jobs with optional filters"""
    query = "SELECT * FROM jobs WHERE 1=1"
    params = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if platform:
        query += " AND platform = ?"
        params.append(platform)
    if city:
        query += " AND city = ?"
        params.append(city)
    query += " ORDER BY match_score DESC, fetched_at DESC"
    
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

@router.get("/{job_id}")
async def get_job(job_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                raise HTTPException(404, "Job not found")
            return dict(row)

@router.put("/{job_id}/cover-letter")
async def update_cover_letter(job_id: str, data: UpdateCoverLetter):
    """Update the cover letter for a job"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE jobs SET cover_letter=? WHERE id=?", (data.cover_letter, job_id))
        await db.commit()
    return {"success": True}

@router.post("/{job_id}/regenerate-cover-letter")
async def regenerate_cover_letter(job_id: str):
    """Regenerate cover letter with AI"""
    api_key = await get_setting("anthropic_api_key")
    if not api_key:
        raise HTTPException(400, "API key not configured")
    
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)) as cursor:
            job = dict(await cursor.fetchone())
        async with db.execute("SELECT parsed_data FROM resume ORDER BY id DESC LIMIT 1") as cursor:
            row = await cursor.fetchone()
            resume_data = json.loads(row[0])
    
    cover_letter = await generate_cover_letter(job, resume_data, api_key=api_key)
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE jobs SET cover_letter=? WHERE id=?", (cover_letter, job_id))
        await db.commit()
    
    return {"cover_letter": cover_letter}

@router.post("/{job_id}/reject")
async def reject_job(job_id: str, data: RejectJob):
    """Reject a job"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE jobs SET status='rejected', rejection_reason=? WHERE id=?",
            (data.reason, job_id)
        )
        await db.commit()
    return {"success": True}

@router.delete("/clear-rejected")
async def clear_rejected():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM jobs WHERE status='rejected'")
        await db.commit()
    return {"success": True}
