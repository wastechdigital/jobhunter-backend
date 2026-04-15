from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
import json
import aiosqlite
from database import get_setting, set_setting, DB_PATH
from services.email_service import send_test_email

router = APIRouter()

class SettingsUpdate(BaseModel):
    anthropic_api_key: Optional[str] = None
    email_address: Optional[str] = None
    email_password: Optional[str] = None
    max_job_age_days: Optional[int] = None
    selected_cities: Optional[List[str]] = None
    selected_platforms: Optional[List[str]] = None
    city_salary_ranges: Optional[Dict[str, Dict[str, int]]] = None
    linkedin_email: Optional[str] = None
    linkedin_password: Optional[str] = None

@router.get("/")
async def get_settings():
    keys = [
        "anthropic_api_key", "email_address", "email_password",
        "max_job_age_days", "selected_cities", "selected_platforms",
        "city_salary_ranges", "linkedin_email", "linkedin_password",
        "indeed_email", "indeed_password"
    ]
    result = {}
    for key in keys:
        val = await get_setting(key)
        if key in ("selected_cities", "selected_platforms", "city_salary_ranges"):
            result[key] = json.loads(val) if val else ([] if "cities" in key or "platforms" in key else {})
        elif key in ("anthropic_api_key", "email_password", "linkedin_password", "indeed_password"):
            result[key] = "***" if val else ""
        else:
            result[key] = val
    return result

@router.put("/")
async def update_settings(data: SettingsUpdate):
    updates = data.model_dump(exclude_none=True)
    for key, value in updates.items():
        if isinstance(value, (dict, list)):
            await set_setting(key, json.dumps(value))
        else:
            await set_setting(key, str(value))
    return {"success": True, "updated": list(updates.keys())}

@router.post("/test-email")
async def test_email():
    email = await get_setting("email_address")
    password = await get_setting("email_password")
    if not email or not password:
        raise HTTPException(400, "Email credentials not configured")
    try:
        await send_test_email(email, email, password)
        return {"success": True, "message": f"Test email sent to {email}"}
    except Exception as e:
        raise HTTPException(400, f"Email test failed: {str(e)}")
