import aiohttp
import json
from datetime import datetime

RESEND_API_KEY = "re_YzgB6tD5_2hFwmfJxkLQjWvTxKcpzaa3k"
RESEND_URL = "https://api.resend.com/emails"
FROM_EMAIL = "JobHunter AI <onboarding@resend.dev>"

async def send_via_resend(to_email: str, subject: str, html: str) -> bool:
    payload = {
        "from": FROM_EMAIL,
        "to": [to_email],
        "subject": subject,
        "html": html
    }
    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json"
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(RESEND_URL, json=payload, headers=headers) as resp:
            body = await resp.json()
            if resp.status in (200, 201):
                return True
            raise Exception(f"Resend error {resp.status}: {body}")

async def send_application_email(
    to_email: str,
    smtp_user: str,
    smtp_password: str,
    job: dict,
    cover_letter: str,
    **kwargs
):
    subject = f"✅ Application Sent: {job.get('title')} at {job.get('company')}"
    html = f"""
<!DOCTYPE html>
<html>
<head>
<style>
  body {{ font-family: 'Segoe UI', sans-serif; background: #0f0f1a; color: #e0e0f0; margin: 0; padding: 20px; }}
  .card {{ background: #1a1a2e; border: 1px solid #2d2d5e; border-radius: 12px; padding: 24px; max-width: 600px; margin: auto; }}
  .header {{ background: linear-gradient(135deg, #4f46e5, #7c3aed); padding: 20px 24px; border-radius: 8px; margin-bottom: 20px; }}
  .header h1 {{ color: white; margin: 0; font-size: 20px; }}
  .badge {{ display: inline-block; background: #4f46e5; color: white; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; }}
  .detail {{ padding: 8px 0; border-bottom: 1px solid #2d2d5e; }}
  .detail strong {{ color: #a78bfa; }}
  .cover-letter {{ background: #0f0f1a; border: 1px solid #2d2d5e; border-radius: 8px; padding: 16px; margin-top: 16px; white-space: pre-line; font-size: 14px; line-height: 1.6; }}
  .footer {{ margin-top: 20px; font-size: 12px; color: #6b7280; text-align: center; }}
</style>
</head>
<body>
<div class="card">
  <div class="header">
    <h1>🚀 Application Submitted</h1>
    <p style="color: #c4b5fd; margin: 4px 0 0;">JobHunter AI · {datetime.now().strftime('%B %d, %Y at %H:%M')}</p>
  </div>
  <span class="badge">{job.get('platform','').upper()}</span>
  <div class="detail" style="margin-top: 12px;"><strong>Position:</strong> {job.get('title')}</div>
  <div class="detail"><strong>Company:</strong> {job.get('company')}</div>
  <div class="detail"><strong>Location:</strong> {job.get('location')}</div>
  <div class="detail"><strong>Job URL:</strong> <a href="{job.get('url')}" style="color: #818cf8;">{job.get('url','')[:80]}</a></div>
  <div class="detail"><strong>Match Score:</strong> {job.get('match_score', 0):.0f}%</div>
  <h3 style="color: #a78bfa; margin-top: 20px;">Cover Letter Sent:</h3>
  <div class="cover-letter">{cover_letter}</div>
  <div class="footer">Sent by JobHunter AI · Track your applications in your dashboard</div>
</div>
</body>
</html>
"""
    return await send_via_resend(to_email, subject, html)

async def send_test_email(to_email: str, smtp_user: str = "", smtp_password: str = "") -> bool:
    subject = "✅ JobHunter AI - Email Test Successful"
    html = """
<html><body style="font-family:sans-serif;background:#0f0f1a;color:#e0e0f0;padding:20px;">
<div style="background:#1a1a2e;padding:24px;border-radius:12px;max-width:500px;margin:auto;border:1px solid #2d2d5e;">
<h2 style="color:#a78bfa;">✅ Email Notifications Working!</h2>
<p>Your JobHunter AI is configured correctly. You will receive an email copy every time a job application is submitted.</p>
<p style="color:#6b7280;font-size:12px;">JobHunter AI · Powered by Resend</p>
</div></body></html>
"""
    return await send_via_resend(to_email, subject, html)
