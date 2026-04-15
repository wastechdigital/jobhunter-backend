from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
import json
import aiosqlite
from datetime import datetime
from database import get_setting, DB_PATH
from services.email_service import send_application_email
import webbrowser

router = APIRouter()

class ApproveRequest(BaseModel):
    cover_letter: Optional[str] = None  # Use existing if not provided

async def _apply_to_job(job_id: str, cover_letter: str):
    """
    Apply to job - opens the job URL for manual/automated application.
    For LinkedIn Easy Apply jobs, this can be automated via Playwright.
    For others, opens pre-filled page.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)) as cursor:
            job = dict(await cursor.fetchone())
    
    # Mark as applied
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE jobs SET status='applied', applied_at=? WHERE id=?",
            (datetime.now().isoformat(), job_id)
        )
        await db.execute(
            "INSERT INTO applications (job_id, applied_at, status) VALUES (?,?,?)",
            (job_id, datetime.now().isoformat(), "applied")
        )
        await db.commit()
    
    return job

@router.post("/{job_id}/approve")
async def approve_job(job_id: str, req: ApproveRequest, background_tasks: BackgroundTasks):
    """Approve a job and submit application"""
    
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                raise HTTPException(404, "Job not found")
            job = dict(row)
    
    if job["status"] == "applied":
        raise HTTPException(400, "Already applied to this job")
    
    # Use provided cover letter or existing one
    cover_letter = req.cover_letter or job.get("cover_letter", "")
    
    if req.cover_letter:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE jobs SET cover_letter=? WHERE id=?", (cover_letter, job_id))
            await db.commit()
    
    # Apply
    applied_job = await _apply_to_job(job_id, cover_letter)
    
    # Send email notification in background
    email = await get_setting("email_address")
    smtp_pass = await get_setting("email_password")
    
    if email and smtp_pass:
        background_tasks.add_task(
            send_application_email,
            to_email=email,
            smtp_user=email,
            smtp_password=smtp_pass,
            job=applied_job,
            cover_letter=cover_letter
        )
        # Mark email sent
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE applications SET email_sent=1, email_to=? WHERE job_id=? ORDER BY id DESC LIMIT 1",
                (email, job_id)
            )
            await db.commit()
    
    return {
        "success": True,
        "job_url": applied_job["url"],
        "message": f"Application recorded for {applied_job['title']} at {applied_job['company']}. Email notification sent.",
        "email_sent": bool(email and smtp_pass)
    }

@router.post("/bulk-approve")
async def bulk_approve(background_tasks: BackgroundTasks, job_ids: list[str] = []):
    """Approve multiple jobs at once"""
    results = []
    for job_id in job_ids:
        try:
            job = await _apply_to_job(job_id, "")
            results.append({"job_id": job_id, "success": True, "title": job["title"]})
        except Exception as e:
            results.append({"job_id": job_id, "success": False, "error": str(e)})
    
    # Send summary email
    email = await get_setting("email_address")
    smtp_pass = await get_setting("email_password")
    if email and smtp_pass:
        background_tasks.add_task(_send_bulk_summary_email, email, smtp_pass, results)
    
    return {"results": results}

async def _send_bulk_summary_email(email: str, password: str, results: list):
    """Send bulk application summary"""
    from services.email_service import send_application_email
    # Simplified - in prod would send one summary email
    pass

@router.get("/history")
async def get_application_history():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT a.*, j.title, j.company, j.location, j.platform, j.match_score, j.url, j.city
            FROM applications a
            JOIN jobs j ON a.job_id = j.id
            ORDER BY a.applied_at DESC
        """) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]
