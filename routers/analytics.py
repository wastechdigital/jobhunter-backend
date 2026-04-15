from fastapi import APIRouter
import aiosqlite
import json
from database import DB_PATH

router = APIRouter()

@router.get("/dashboard")
async def get_dashboard():
    async with aiosqlite.connect(DB_PATH) as db:
        # Counts by status
        async with db.execute("SELECT status, COUNT(*) as cnt FROM jobs GROUP BY status") as c:
            status_rows = await c.fetchall()
        status_counts = {r[0]: r[1] for r in status_rows}
        
        # By platform
        async with db.execute("SELECT platform, COUNT(*) as cnt FROM jobs GROUP BY platform") as c:
            platform_rows = await c.fetchall()
        platform_counts = {r[0]: r[1] for r in platform_rows}
        
        # By city
        async with db.execute("SELECT city, COUNT(*) as cnt FROM jobs GROUP BY city") as c:
            city_rows = await c.fetchall()
        city_counts = {r[0]: r[1] for r in city_rows}
        
        # Applied jobs with details
        async with db.execute("""
            SELECT j.title, j.company, j.platform, j.city, j.match_score, j.applied_at, j.url
            FROM jobs j WHERE j.status='applied' ORDER BY j.applied_at DESC LIMIT 20
        """) as c:
            applied_rows = await c.fetchall()
        applied = [{"title":r[0],"company":r[1],"platform":r[2],"city":r[3],"match_score":r[4],"applied_at":r[5],"url":r[6]} for r in applied_rows]
        
        # Match score distribution
        async with db.execute("""
            SELECT 
                CASE 
                    WHEN match_score >= 80 THEN '80-100'
                    WHEN match_score >= 60 THEN '60-79'
                    WHEN match_score >= 40 THEN '40-59'
                    ELSE '0-39'
                END as bucket,
                COUNT(*) as cnt
            FROM jobs GROUP BY bucket
        """) as c:
            score_rows = await c.fetchall()
        score_dist = {r[0]: r[1] for r in score_rows}
        
        # Top matching jobs not yet applied
        async with db.execute("""
            SELECT id, title, company, platform, city, match_score, url
            FROM jobs WHERE status='pending_review'
            ORDER BY match_score DESC LIMIT 5
        """) as c:
            top_rows = await c.fetchall()
        top_pending = [{"id":r[0],"title":r[1],"company":r[2],"platform":r[3],"city":r[4],"match_score":r[5],"url":r[6]} for r in top_rows]
        
        # Daily applications trend (last 14 days)
        async with db.execute("""
            SELECT DATE(applied_at) as day, COUNT(*) as cnt 
            FROM jobs WHERE status='applied' AND applied_at IS NOT NULL
            GROUP BY day ORDER BY day DESC LIMIT 14
        """) as c:
            trend_rows = await c.fetchall()
        trend = [{"date": r[0], "count": r[1]} for r in reversed(trend_rows)]
        
        return {
            "summary": {
                "total_found": sum(status_counts.values()),
                "pending_review": status_counts.get("pending_review", 0),
                "applied": status_counts.get("applied", 0),
                "rejected": status_counts.get("rejected", 0),
            },
            "by_platform": platform_counts,
            "by_city": city_counts,
            "score_distribution": score_dist,
            "recent_applications": applied,
            "top_pending": top_pending,
            "application_trend": trend,
        }
