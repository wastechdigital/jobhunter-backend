from fastapi import APIRouter, UploadFile, File, HTTPException
import anthropic
import json
import os
import PyPDF2
import io
from database import get_setting, set_setting, DB_PATH
import aiosqlite
from datetime import datetime

router = APIRouter()

async def extract_text_from_pdf(file_bytes: bytes) -> str:
    reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text

async def parse_resume_with_ai(resume_text: str, api_key: str) -> dict:
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": f"""Analyze this resume and extract structured information. Return ONLY valid JSON, no markdown.

Resume:
{resume_text}

Return JSON with these exact keys:
{{
  "name": "full name",
  "email": "email",
  "phone": "phone",
  "location": "current location",
  "title": "current/desired job title",
  "years_experience": number,
  "skills": ["skill1", "skill2"],
  "tools": ["tool1", "tool2"],
  "certifications": ["cert1"],
  "education": [{{"degree": "", "field": "", "institution": "", "year": ""}}],
  "experience": [{{"title": "", "company": "", "duration": "", "highlights": [""]}}],
  "languages": ["English", "etc"],
  "suitable_roles": ["role1", "role2", "role3", "role4", "role5"],
  "industry_keywords": ["keyword1", "keyword2"],
  "summary": "2-3 sentence professional summary"
}}"""
        }]
    )
    text = response.content[0].text.strip()
    # Clean any potential markdown
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())

@router.post("/upload")
async def upload_resume(file: UploadFile = File(...)):
    api_key = await get_setting("anthropic_api_key")
    if not api_key:
        raise HTTPException(400, "Anthropic API key not configured. Go to Settings first.")
    
    contents = await file.read()
    
    if file.filename.endswith(".pdf"):
        resume_text = await extract_text_from_pdf(contents)
    else:
        resume_text = contents.decode("utf-8", errors="ignore")
    
    parsed = await parse_resume_with_ai(resume_text, api_key)
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM resume")
        await db.execute(
            "INSERT INTO resume (filename, content, parsed_data, uploaded_at) VALUES (?, ?, ?, ?)",
            (file.filename, resume_text, json.dumps(parsed), datetime.now().isoformat())
        )
        await db.commit()
    
    return {"success": True, "parsed": parsed, "filename": file.filename}

@router.get("/current")
async def get_resume():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT filename, parsed_data, uploaded_at FROM resume ORDER BY id DESC LIMIT 1") as cursor:
            row = await cursor.fetchone()
            if not row:
                return {"resume": None}
            return {
                "resume": {
                    "filename": row[0],
                    "parsed": json.loads(row[1]),
                    "uploaded_at": row[2]
                }
            }
