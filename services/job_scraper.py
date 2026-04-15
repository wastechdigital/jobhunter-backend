import asyncio
import aiohttp
import json
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import hashlib

async def search_linkedin_jobs(query: str, location: str, max_age_days: int) -> List[Dict]:
    """Search LinkedIn jobs via public job search API"""
    jobs = []
    try:
        # LinkedIn public job search (no auth required for listings)
        url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
        params = {
            "keywords": query,
            "location": location,
            "f_TPR": f"r{max_age_days * 86400}",  # time range in seconds
            "start": 0,
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml",
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers, timeout=10) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    # Parse job cards from HTML
                    job_ids = re.findall(r'data-entity-urn="urn:li:jobPosting:(\d+)"', html)
                    titles = re.findall(r'class="base-search-card__title"[^>]*>([^<]+)<', html)
                    companies = re.findall(r'class="base-search-card__subtitle"[^>]*>\s*<[^>]+>([^<]+)<', html)
                    locations = re.findall(r'class="job-search-card__location"[^>]*>([^<]+)<', html)
                    
                    for i, job_id in enumerate(job_ids[:20]):
                        jobs.append({
                            "id": f"linkedin_{job_id}",
                            "platform": "linkedin",
                            "title": titles[i].strip() if i < len(titles) else query,
                            "company": companies[i].strip() if i < len(companies) else "Unknown",
                            "location": locations[i].strip() if i < len(locations) else location,
                            "city": location,
                            "url": f"https://www.linkedin.com/jobs/view/{job_id}/",
                            "description": "",
                            "salary": "",
                            "posted_date": datetime.now().isoformat(),
                        })
    except Exception as e:
        print(f"LinkedIn search error: {e}")
    return jobs

async def search_indeed_jobs(query: str, location: str, max_age_days: int) -> List[Dict]:
    """Search Indeed jobs"""
    jobs = []
    try:
        url = "https://ae.indeed.com/jobs"
        params = {
            "q": query,
            "l": location,
            "fromage": str(max_age_days),
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers, timeout=10) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    # Extract job cards
                    job_blocks = re.findall(r'data-jk="([^"]+)"', html)
                    titles = re.findall(r'class="jobTitle[^"]*"[^>]*><[^>]+>([^<]+)<', html)
                    companies = re.findall(r'data-testid="company-name"[^>]*>([^<]+)<', html)
                    locs = re.findall(r'data-testid="text-location"[^>]*>([^<]+)<', html)
                    
                    for i, jk in enumerate(job_blocks[:20]):
                        jobs.append({
                            "id": f"indeed_{jk}",
                            "platform": "indeed",
                            "title": titles[i].strip() if i < len(titles) else query,
                            "company": companies[i].strip() if i < len(companies) else "Unknown",
                            "location": locs[i].strip() if i < len(locs) else location,
                            "city": location,
                            "url": f"https://ae.indeed.com/viewjob?jk={jk}",
                            "description": "",
                            "salary": "",
                            "posted_date": datetime.now().isoformat(),
                        })
    except Exception as e:
        print(f"Indeed search error: {e}")
    return jobs

async def search_bayt_jobs(query: str, location: str, max_age_days: int) -> List[Dict]:
    """Search Bayt.com jobs"""
    jobs = []
    try:
        location_slug = location.lower().replace(" ", "-")
        url = f"https://www.bayt.com/en/uae/jobs/{query.lower().replace(' ', '-')}-jobs-in-{location_slug}/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml",
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=10) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    # Parse Bayt job listings
                    titles = re.findall(r'data-js-aid="JobsSearchResults"[^>]*>.*?<h2[^>]*>([^<]+)<', html, re.DOTALL)
                    job_urls = re.findall(r'href="(/en/uae/jobs/[^"]+/\d+/)"', html)
                    companies = re.findall(r'class="jb-company"[^>]*>([^<]+)<', html)
                    locs = re.findall(r'class="jb-loc"[^>]*>([^<]+)<', html)
                    
                    # Alternative extraction
                    if not titles:
                        titles_match = re.findall(r'"jobTitle"\s*:\s*"([^"]+)"', html)
                        titles = titles_match
                    
                    for i, job_url in enumerate(job_urls[:20]):
                        job_id = hashlib.md5(job_url.encode()).hexdigest()[:12]
                        jobs.append({
                            "id": f"bayt_{job_id}",
                            "platform": "bayt",
                            "title": titles[i].strip() if i < len(titles) else query,
                            "company": companies[i].strip() if i < len(companies) else "Unknown",
                            "location": locs[i].strip() if i < len(locs) else location,
                            "city": location,
                            "url": f"https://www.bayt.com{job_url}",
                            "description": "",
                            "salary": "",
                            "posted_date": datetime.now().isoformat(),
                        })
    except Exception as e:
        print(f"Bayt search error: {e}")
    return jobs

async def search_naukrigulf_jobs(query: str, location: str, max_age_days: int) -> List[Dict]:
    """Search Naukrigulf jobs"""
    jobs = []
    try:
        url = "https://www.naukrigulf.com/jobs-in-uae"
        params = {
            "q": query,
            "loc": location,
            "xp": "0-20",
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers, timeout=10) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    job_ids = re.findall(r'data-job-id="(\d+)"', html)
                    titles = re.findall(r'class="designation"[^>]*><[^>]+>([^<]+)<', html)
                    companies = re.findall(r'class="company-name"[^>]*>([^<]+)<', html)
                    locs = re.findall(r'class="location"[^>]*>([^<]+)<', html)
                    
                    for i, jid in enumerate(job_ids[:20]):
                        jobs.append({
                            "id": f"naukrigulf_{jid}",
                            "platform": "naukrigulf",
                            "title": titles[i].strip() if i < len(titles) else query,
                            "company": companies[i].strip() if i < len(companies) else "Unknown",
                            "location": locs[i].strip() if i < len(locs) else location,
                            "city": location,
                            "url": f"https://www.naukrigulf.com/job/{jid}",
                            "description": "",
                            "salary": "",
                            "posted_date": datetime.now().isoformat(),
                        })
    except Exception as e:
        print(f"Naukrigulf search error: {e}")
    return jobs

async def search_all_platforms(roles: List[str], cities: List[str], platforms: List[str], max_age_days: int) -> List[Dict]:
    """Search all platforms for all roles in all cities"""
    all_jobs = []
    tasks = []
    
    for role in roles[:3]:  # Top 3 roles
        for city in cities:
            if "linkedin" in platforms:
                tasks.append(search_linkedin_jobs(role, city, max_age_days))
            if "indeed" in platforms:
                tasks.append(search_indeed_jobs(role, city, max_age_days))
            if "bayt" in platforms:
                tasks.append(search_bayt_jobs(role, city, max_age_days))
            if "naukrigulf" in platforms:
                tasks.append(search_naukrigulf_jobs(role, city, max_age_days))
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    seen_ids = set()
    for result in results:
        if isinstance(result, list):
            for job in result:
                if job["id"] not in seen_ids:
                    seen_ids.add(job["id"])
                    all_jobs.append(job)
    
    return all_jobs
