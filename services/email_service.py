import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
import os

async def send_application_email(
    to_email: str,
    smtp_user: str,
    smtp_password: str,
    job: dict,
    cover_letter: str,
    smtp_host: str = "smtp.gmail.com",
    smtp_port: int = 587
):
    """Send application confirmation email"""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"✅ Job Application Sent: {job['title']} at {job['company']}"
        msg["From"] = smtp_user
        msg["To"] = to_email

        html_body = f"""
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
  <div class="detail"><strong>Job URL:</strong> <a href="{job.get('url')}" style="color: #818cf8;">{job.get('url')[:60]}...</a></div>
  <div class="detail"><strong>Match Score:</strong> {job.get('match_score', 0):.0f}%</div>
  
  <h3 style="color: #a78bfa; margin-top: 20px;">Cover Letter Sent:</h3>
  <div class="cover-letter">{cover_letter}</div>
  
  <div class="footer">
    Sent by JobHunter AI · Track your applications in your dashboard
  </div>
</div>
</body>
</html>
"""
        msg.attach(MIMEText(html_body, "html"))
        
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, to_email, msg.as_string())
        
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

async def send_test_email(to_email: str, smtp_user: str, smtp_password: str) -> bool:
    """Send a test email to verify SMTP config"""
    try:
        msg = MIMEMultipart()
        msg["Subject"] = "✅ JobHunter AI - Email Test Successful"
        msg["From"] = smtp_user
        msg["To"] = to_email
        
        html = """<html><body style="font-family:sans-serif;background:#0f0f1a;color:#e0e0f0;padding:20px;">
<div style="background:#1a1a2e;padding:24px;border-radius:12px;max-width:500px;margin:auto;border:1px solid #2d2d5e;">
<h2 style="color:#a78bfa;">✅ Email Configuration Working!</h2>
<p>Your JobHunter AI email notifications are set up correctly. You'll receive an email like this every time a job application is submitted.</p>
<p style="color:#6b7280;font-size:12px;">JobHunter AI</p>
</div></body></html>"""
        
        msg.attach(MIMEText(html, "html"))
        
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"Test email error: {e}")
        raise Exception(str(e))
