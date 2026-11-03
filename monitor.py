import os
import sys
import time
import argparse
import logging
import threading
import smtplib
from email.message import EmailMessage
from datetime import datetime
import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template_string

# Load environment variables from .env file if available
load_dotenv()

# Configuration
PORTAL_URL = "https://vtu.internyet.in/internships?sort_by=latest&category_ids%5B%5D=1&category_ids%5B%5D=2&category_ids%5B%5D=9&internship_type=Free&internship_mode=Remote"
API_URL = "https://vtuapi.internyet.in/api/v1/internships"

SENDER_EMAIL = os.getenv("SENDER_EMAIL", "your_email@gmail.com")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD", "your_app_password")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL", "prateekpkini2005@gmail.com")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL_SECONDS", "60"))
PORT = int(os.getenv("PORT", "10000"))

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("VTU_Monitor")

# Global Monitor State (for web dashboard & health check)
monitor_status = {
    "is_running": True,
    "last_check_time": None,
    "total_tracked": 0,
    "latest_internship": None,
    "total_alerts_sent": 0,
    "errors_count": 0,
    "recipient_email": RECIPIENT_EMAIL,
}
status_lock = threading.Lock()

# Flask App for Render Port Binding
app = Flask(__name__)

HTML_DASHBOARD = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VTU Internship Monitor</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background: #0f172a; color: #f8fafc; padding: 20px; margin: 0; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        .card { background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 28px; max-width: 580px; width: 100%; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.3); }
        .badge { background: #10b981; color: #ffffff; padding: 4px 10px; border-radius: 9999px; font-size: 13px; font-weight: 600; display: inline-block; }
        h1 { margin-top: 12px; margin-bottom: 6px; font-size: 22px; color: #ffffff; }
        p.sub { color: #94a3b8; font-size: 14px; margin-top: 0; margin-bottom: 20px; }
        .stat-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 20px; }
        .stat-box { background: #0f172a; padding: 14px; border-radius: 8px; border: 1px solid #334155; }
        .stat-label { font-size: 12px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; }
        .stat-value { font-size: 18px; font-weight: bold; color: #38bdf8; }
        .detail-box { background: #0f172a; padding: 14px; border-radius: 8px; border: 1px solid #334155; font-size: 14px; margin-bottom: 16px; }
        .btn { display: inline-block; background: #2563eb; color: #ffffff; text-decoration: none; padding: 8px 16px; border-radius: 6px; font-weight: 600; font-size: 13px; margin-top: 8px; }
        .btn:hover { background: #1d4ed8; }
    </style>
</head>
<body>
    <div class="card">
        <span class="badge">● Active &amp; Polling</span>
        <h1>VTU Internship Monitor</h1>
        <p class="sub">Automated real-time scanner for Free &amp; Remote VTU internships</p>
        
        <div class="stat-grid">
            <div class="stat-box">
                <div class="stat-label">Tracked Internships</div>
                <div class="stat-value">{{ status.total_tracked }}</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">Alerts Fired</div>
                <div class="stat-value">{{ status.total_alerts_sent }}</div>
            </div>
        </div>

        <div class="detail-box">
            <strong>📧 Recipient:</strong> {{ status.recipient_email }}<br>
            <strong>⏱️ Last Checked:</strong> {{ status.last_check_time or "Initializing..." }}<br>
            {% if status.latest_internship %}
            <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #334155;">
                <strong>🆕 Latest Detected:</strong><br>
                {{ status.latest_internship }}
            </div>
            {% endif %}
        </div>

        <a class="btn" href="{{ portal_url }}" target="_blank">Open VTU Portal Filter &rarr;</a>
    </div>
</body>
</html>
"""


@app.route("/")
def home():
    """Render status page to satisfy Render HTTP health checks."""
    with status_lock:
        current_status = dict(monitor_status)
    return render_template_string(HTML_DASHBOARD, status=current_status, portal_url=PORTAL_URL)


@app.route("/health")
def health():
    """JSON health endpoint for uptime monitors."""
    with status_lock:
        return jsonify({
            "status": "healthy",
            "monitor": monitor_status
        }), 200


def fetch_latest_internships():
    """
    Fetch internship listings directly from the VTU Internyet API.
    Returns a list of dicts representing the internships.
    """
    params = {
        "sort_by": "latest",
        "category_ids[]": ["1", "2", "9"],
        "internship_type": "Free",
        "internship_mode": "Remote",
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Referer": "https://vtu.internyet.in/",
    }

    try:
        response = requests.get(API_URL, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()

        if isinstance(data, dict) and "data" in data:
            raw_data = data["data"]
            if isinstance(raw_data, dict) and "data" in raw_data:
                return raw_data["data"]
            elif isinstance(raw_data, list):
                return raw_data

        logger.warning("Unexpected API response structure.")
        return []
    except Exception as e:
        logger.error(f"Error fetching from VTU API: {e}")
        with status_lock:
            monitor_status["errors_count"] += 1
        return []


def build_email_content(new_internships):
    """
    Constructs both plain text and HTML versions of the email alert.
    """
    count = len(new_internships)
    subject = f"🚨 VTU Internship Alert: {count} New Free/Remote Listing{'s' if count > 1 else ''} Found!"

    text_lines = [
        f"🚨 A new internship update was detected on the VTU Portal!",
        f"",
        f"Portal Filter: {PORTAL_URL}",
        f"",
        f"--- New Listings ({count}) ---",
    ]

    for item in new_internships:
        title = item.get("title", "Untitled Internship")
        company = item.get("company", {}).get("name") if isinstance(item.get("company"), dict) else item.get("company_name", "N/A")
        slug = item.get("slug", "")
        item_url = f"https://vtu.internyet.in/internships/{slug}" if slug else PORTAL_URL
        duration = item.get("duration", "N/A")
        work_mode = item.get("workMode", "Remote")
        deadline = item.get("deadline", "N/A")
        positions = item.get("number_of_positions", "N/A")
        desc = item.get("description", "")
        if desc and len(desc) > 200:
            desc = desc[:200] + "..."

        text_lines.append(f"\n• {title}")
        text_lines.append(f"  Company:   {company}")
        text_lines.append(f"  Mode/Type: {work_mode} | {item.get('type', 'Free')}")
        text_lines.append(f"  Duration:  {duration} month(s) | Positions: {positions}")
        text_lines.append(f"  Deadline:  {deadline}")
        text_lines.append(f"  Apply:     {item_url}")
        if desc:
            text_lines.append(f"  Details:   {desc}")

    text_body = "\n".join(text_lines)

    items_html = ""
    for item in new_internships:
        title = item.get("title", "Untitled Internship")
        company = item.get("company", {}).get("name") if isinstance(item.get("company"), dict) else item.get("company_name", "N/A")
        slug = item.get("slug", "")
        item_url = f"https://vtu.internyet.in/internships/{slug}" if slug else PORTAL_URL
        duration = item.get("duration", "N/A")
        work_mode = item.get("workMode", "Remote")
        deadline = item.get("deadline", "N/A")
        positions = item.get("number_of_positions", "N/A")
        desc = item.get("description", "")
        if desc and len(desc) > 250:
            desc = desc[:250] + "..."

        items_html += f"""
        <div style="border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin-bottom: 16px; background-color: #ffffff;">
            <h3 style="margin: 0 0 8px 0; color: #1e3a8a; font-size: 18px;">{title}</h3>
            <p style="margin: 4px 0; color: #475569; font-weight: bold;">🏢 Company: <span style="color: #0f172a;">{company}</span></p>
            <p style="margin: 4px 0; color: #475569;">📍 Mode: <span style="color: #059669; font-weight: 600;">{work_mode}</span> | 💰 Type: <span style="color: #2563eb; font-weight: 600;">{item.get('type', 'Free')}</span></p>
            <p style="margin: 4px 0; color: #475569;">⏳ Duration: {duration} months | 👥 Positions: {positions} | 📅 Deadline: {deadline}</p>
            {f'<p style="margin: 8px 0; font-size: 14px; color: #64748b; line-height: 1.4;">{desc}</p>' if desc else ''}
            <div style="margin-top: 12px;">
                <a href="{item_url}" style="background-color: #2563eb; color: #ffffff; padding: 8px 16px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">View & Apply &rarr;</a>
            </div>
        </div>
        """

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f8fafc; padding: 20px; color: #1e293b;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 10px; padding: 24px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);">
            <div style="border-bottom: 2px solid #3b82f6; padding-bottom: 12px; margin-bottom: 20px;">
                <h1 style="color: #1e40af; margin: 0; font-size: 22px;">🚨 New VTU Internship Alert!</h1>
                <p style="margin: 4px 0 0 0; color: #64748b; font-size: 14px;">Found {count} new internship posting{'s' if count > 1 else ''} on the VTU Portal.</p>
            </div>
            {items_html}
            <div style="margin-top: 24px; padding-top: 16px; border-top: 1px solid #e2e8f0; font-size: 12px; color: #94a3b8; text-align: center;">
                <p>Sent by VTU Internship Monitor. <a href="{PORTAL_URL}">Open Portal Filter</a></p>
            </div>
        </div>
    </body>
    </html>
    """

    return subject, text_body, html_body


def send_email_alert(new_internships):
    """
    Sends an instant email alert via Gmail SMTP SSL.
    """
    if SENDER_EMAIL in ("your_email@gmail.com", "") or SENDER_PASSWORD in ("your_app_password", ""):
        logger.warning(
            "⚠️  Gmail credentials not configured! Please set SENDER_EMAIL and SENDER_PASSWORD in your .env or environment variables."
        )
        logger.info(f"Notification would have been sent to: {RECIPIENT_EMAIL}")
        return False

    subject, text_body, html_body = build_email_content(new_internships)

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECIPIENT_EMAIL
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        logger.info(f"✅ Instant email alert sent successfully to {RECIPIENT_EMAIL} ({len(new_internships)} new listing(s))")
        with status_lock:
            monitor_status["total_alerts_sent"] += 1
        return True
    except Exception as e:
        logger.error(f"❌ Failed to send email via SMTP: {e}")
        return False


def run_monitor(single_run=False):
    """
    Background worker loop. Polls VTU internships at CHECK_INTERVAL seconds.
    """
    logger.info("=" * 60)
    logger.info("🚀 Starting VTU Internship Monitor Background Thread")
    logger.info(f"📍 Target Portal : {PORTAL_URL}")
    logger.info(f"📧 Recipient     : {RECIPIENT_EMAIL}")
    logger.info(f"⏱️  Interval      : Every {CHECK_INTERVAL} seconds")
    logger.info("=" * 60)

    # Initial snapshot
    initial_items = fetch_latest_internships()
    known_ids = {item["id"] for item in initial_items if "id" in item}

    with status_lock:
        monitor_status["last_check_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        monitor_status["total_tracked"] = len(known_ids)
        if initial_items:
            first = initial_items[0]
            company = first.get("company", {}).get("name") if isinstance(first.get("company"), dict) else first.get("company_name", "N/A")
            monitor_status["latest_internship"] = f"{first.get('title')} ({company})"

    logger.info(f"Initial sync complete: tracking {len(known_ids)} existing internships.")

    if initial_items:
        first = initial_items[0]
        logger.info(f"Latest existing: [{first.get('id')}] {first.get('title')}")

    if single_run:
        logger.info("Single run flag set. Exiting background loop.")
        return

    while True:
        try:
            time.sleep(CHECK_INTERVAL)
            current_items = fetch_latest_internships()
            if not current_items:
                continue

            current_ids = {item["id"] for item in current_items if "id" in item}
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            with status_lock:
                monitor_status["last_check_time"] = now_str
                monitor_status["total_tracked"] = len(current_ids)

            # Check for brand new internship IDs
            new_ids = current_ids - known_ids
            if new_ids:
                new_items = [item for item in current_items if item.get("id") in new_ids]
                logger.info(f"🔔 CHANGE DETECTED! Found {len(new_items)} new internship(s)!")
                for item in new_items:
                    logger.info(f"  + [{item.get('id')}] {item.get('title')}")

                send_email_alert(new_items)
                known_ids.update(new_ids)

                with status_lock:
                    first_new = new_items[0]
                    company = first_new.get("company", {}).get("name") if isinstance(first_new.get("company"), dict) else first_new.get("company_name", "N/A")
                    monitor_status["latest_internship"] = f"{first_new.get('title')} ({company})"
            else:
                logger.debug(f"Check completed: no new internships. (Total tracked: {len(known_ids)})")

        except Exception as e:
            logger.error(f"Unexpected error in monitor loop: {e}")
            time.sleep(10)


def send_test_email():
    """
    Send a test notification with mock data to verify Gmail SMTP setup.
    """
    logger.info(f"Sending test alert to {RECIPIENT_EMAIL} using {SENDER_EMAIL}...")
    sample_data = [{
        "id": 99999,
        "title": "Software Engineering Intern (Test Alert)",
        "company": {"name": "Test Technologies"},
        "slug": "test-internship",
        "type": "Free",
        "workMode": "Remote",
        "duration": "3",
        "number_of_positions": 10,
        "deadline": datetime.now().strftime("%Y-%m-%d"),
        "description": "This is a test notification from VTU Internship Monitor confirming your Gmail SMTP setup is working correctly."
    }]
    if send_email_alert(sample_data):
        logger.info("🎉 Test email succeeded! Your email configuration is working.")
    else:
        logger.warning("Test email failed or credentials are missing. Check logs above.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VTU Internship Monitor")
    parser.add_argument("--test-email", action="store_true", help="Send a test email to verify credentials")
    parser.add_argument("--once", action="store_true", help="Run a single fetch check and exit without starting Flask")
    parser.add_argument("--no-server", action="store_true", help="Run monitor in main thread without starting Flask web server")
    args = parser.parse_args()

    if args.test_email:
        send_test_email()
    elif args.once:
        run_monitor(single_run=True)
    elif args.no_server:
        run_monitor(single_run=False)
    else:
        # Start background monitor in a daemon thread
        monitor_thread = threading.Thread(target=run_monitor, daemon=True)
        monitor_thread.start()

        # Run Flask web server to satisfy Render's port binding requirement
        logger.info(f"🌐 Starting Flask web server on port {PORT} for Render port binding...")
        app.run(host="0.0.0.0", port=PORT)
