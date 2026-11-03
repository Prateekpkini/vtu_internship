import os
import sys
import time
import argparse
import logging
import smtplib
from email.message import EmailMessage
from datetime import datetime
import requests
from dotenv import load_dotenv

# Load environment variables from .env file if available
load_dotenv()

# Configuration
PORTAL_URL = "https://vtu.internyet.in/internships?sort_by=latest&category_ids%5B%5D=1&category_ids%5B%5D=2&category_ids%5B%5D=9&internship_type=Free&internship_mode=Remote"
API_URL = "https://vtuapi.internyet.in/api/v1/internships"

SENDER_EMAIL = os.getenv("SENDER_EMAIL", "your_email@gmail.com")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD", "your_app_password")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL", "prateekpkini2005@gmail.com")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL_SECONDS", "60"))

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("VTU_Monitor")


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

        # The API wraps listings under data.data
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
        return []


def build_email_content(new_internships):
    """
    Constructs both plain text and HTML versions of the email alert.
    """
    count = len(new_internships)
    subject = f"🚨 VTU Internship Alert: {count} New Free/Remote Listing{'s' if count > 1 else ''} Found!"

    # Plain text format
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

    # HTML format
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
            "⚠️  Gmail credentials not configured! Please set SENDER_EMAIL and SENDER_PASSWORD in your .env file."
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
        return True
    except Exception as e:
        logger.error(f"❌ Failed to send email via SMTP: {e}")
        return False


def run_monitor(single_run=False):
    """
    Main monitor loop. Polls VTU internships at CHECK_INTERVAL seconds.
    """
    logger.info("=" * 60)
    logger.info("🚀 Starting VTU Internship Monitor")
    logger.info(f"📍 Target Portal : {PORTAL_URL}")
    logger.info(f"📧 Recipient     : {RECIPIENT_EMAIL}")
    logger.info(f"⏱️  Interval      : Every {CHECK_INTERVAL} seconds")
    logger.info("=" * 60)

    # Initial snapshot
    initial_items = fetch_latest_internships()
    known_ids = {item["id"] for item in initial_items if "id" in item}
    logger.info(f"Initial sync complete: tracking {len(known_ids)} existing internships.")

    if initial_items:
        first = initial_items[0]
        logger.info(f"Latest existing: [{first.get('id')}] {first.get('title')} ({first.get('company', {}).get('name', 'N/A')})")

    if single_run:
        logger.info("Single run flag set. Exiting.")
        return

    while True:
        try:
            time.sleep(CHECK_INTERVAL)
            current_items = fetch_latest_internships()
            if not current_items:
                continue

            current_ids = {item["id"] for item in current_items if "id" in item}

            # Check for brand new internship IDs
            new_ids = current_ids - known_ids
            if new_ids:
                new_items = [item for item in current_items if item.get("id") in new_ids]
                logger.info(f"🔔 CHANGE DETECTED! Found {len(new_items)} new internship(s)!")
                for item in new_items:
                    logger.info(f"  + [{item.get('id')}] {item.get('title')}")

                send_email_alert(new_items)
                known_ids.update(new_ids)
            else:
                logger.debug(f"Check completed: no new internships. (Total tracked: {len(known_ids)})")

        except KeyboardInterrupt:
            logger.info("Monitor stopped by user.")
            break
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
    parser.add_argument("--once", action="store_true", help="Run a single fetch check and exit")
    args = parser.parse_args()

    if args.test_email:
        send_test_email()
    else:
        run_monitor(single_run=args.once)

