import anthropic
import json
from typing import List, Dict

async def score_and_enrich_jobs(jobs: List[Dict], resume_data: dict, api_key: str) -> List[Dict]:
    """Score jobs against resume and generate cover letters for top matches"""
    if not jobs:
        return []
    
    client = anthropic.Anthropic(api_key=api_key)
    
    # Score all jobs in one batch call
    jobs_summary = []
    for i, job in enumerate(jobs[:50]):
        jobs_summary.append(f"{i}. [{job['platform'].upper()}] {job['title']} at {job['company']} - {job['location']}")
    
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": f"""Score these job listings against this resume. Return ONLY JSON array, no markdown.

Candidate: {resume_data.get('name')}
Title: {resume_data.get('title')}
Skills: {', '.join(resume_data.get('skills', [])[:15])}
Tools: {', '.join(resume_data.get('tools', [])[:10])}
Experience: {resume_data.get('years_experience')} years
Certifications: {', '.join(resume_data.get('certifications', []))}

Jobs:
{chr(10).join(jobs_summary)}

Return JSON array with one object per job (same index order):
[{{"index": 0, "score": 0-100, "reason": "1 sentence why"}}]

Be strict. Score based on title relevance, required skills match, seniority fit."""
        }]
    )
    
    text = response.content[0].text.strip()
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    
    scores = json.loads(text.strip())
    score_map = {s["index"]: s for s in scores}
    
    enriched = []
    for i, job in enumerate(jobs[:50]):
        score_data = score_map.get(i, {"score": 0, "reason": ""})
        job["match_score"] = score_data.get("score", 0)
        job["match_reason"] = score_data.get("reason", "")
        enriched.append(job)
    
    # Sort by score
    enriched.sort(key=lambda x: x["match_score"], reverse=True)
    
    # Generate cover letters only for top 15 matches
    top_jobs = [j for j in enriched if j["match_score"] >= 50][:15]
    
    for job in top_jobs:
        try:
            cover_letter = await generate_cover_letter(job, resume_data, client)
            job["cover_letter"] = cover_letter
        except Exception as e:
            job["cover_letter"] = ""
    
    return enriched

async def generate_cover_letter(job: Dict, resume_data: dict, client=None, api_key: str = None) -> str:
    """Generate a tailored cover letter for a specific job"""
    if client is None:
        client = anthropic.Anthropic(api_key=api_key)
    
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=800,
        messages=[{
            "role": "user",
            "content": f"""Write a professional cover letter for this job application. Be specific, concise, and compelling. No placeholders.

Candidate:
- Name: {resume_data.get('name')}
- Title: {resume_data.get('title')}
- Experience: {resume_data.get('years_experience')} years
- Skills: {', '.join(resume_data.get('skills', [])[:10])}
- Certifications: {', '.join(resume_data.get('certifications', []))}
- Summary: {resume_data.get('summary')}

Job:
- Title: {job.get('title')}
- Company: {job.get('company')}
- Location: {job.get('location')}
- Platform: {job.get('platform', '').upper()}

Write a 3-paragraph cover letter:
1. Opening: Why this specific role at this company
2. Middle: Most relevant experience and skills (use real numbers/achievements if possible)
3. Closing: Call to action

Keep it under 250 words. Professional but personable tone."""
        }]
    )
    return response.content[0].text.strip()
