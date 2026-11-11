import smtplib
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from urllib.parse import quote
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.encoders import encode_base64
from ics import Calendar, Event
from src.core.config import SystemConfig
from src.core.exceptions import CommunicationError

class GmailDispatcher:
    @staticmethod
    def dispatch_invite(
        to_email, company, date_str, time_str, event_type, uploaded_files=None,
        tz_name="Asia/Kolkata", event_title=None, event_page_url="", accept_url=""
    ):
        config = SystemConfig.validate_and_load()
        sender = config["gmail"]["username"]
        title_display = event_title or f"{company} Programme"

        try:
            local_tz = ZoneInfo(tz_name)
            naive_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            aware_dt = naive_dt.replace(tzinfo=local_tz)
            tz_abbr = aware_dt.strftime("%Z")
            display_time = f"{time_str} {tz_abbr} ({tz_name})"

            msg = MIMEMultipart('mixed')
            msg['Subject'] = f"You are invited to {title_display} ({date_str})"
            msg['From'] = f'"{company}" <{sender}>'
            msg['To'] = to_email

            # Decline still works via direct mailto: link
            metadata = f"| {company} | {date_str} | {time_str} | {event_type} | {tz_name}"
            decline_subject = quote(f"RSVP DECLINE {metadata}")
            decline_body = quote("Send this email as-is to decline the invitation.")
            decline_url = f"mailto:{sender}?subject={decline_subject}&body={decline_body}"

            # Accept & View Event point to the Registration Portal
            final_accept_url = accept_url or event_page_url or f"mailto:{sender}?subject={quote(f'RSVP ACCEPT {metadata}')}"
            final_view_url = event_page_url or final_accept_url

            template_path = os.path.join(os.path.dirname(__file__), '../templates/invite_template.html')
            with open(template_path, 'r', encoding='utf-8') as file:
                html_body = file.read()

            html_body = (
                html_body.replace("{{COMPANY_NAME}}", company)
                         .replace("{{EVENT_TITLE}}", title_display)
                         .replace("{{DATE}}", date_str)
                         .replace("{{TIME}}", display_time)
                         .replace("{{TYPE}}", event_type)
                         .replace("{{ACCEPT_LINK}}", final_accept_url)
                         .replace("{{VIEW_EVENT_LINK}}", final_view_url)
                         .replace("{{DECLINE_LINK}}", decline_url)
            )
            
            msg.attach(MIMEText(html_body, 'html'))

            if uploaded_files:
                for f in uploaded_files:
                    file_part = MIMEBase('application', 'octet-stream')
                    file_part.set_payload(f.read())
                    encode_base64(file_part)
                    file_part.add_header('Content-Disposition', f'attachment; filename="{f.name}"')
                    msg.attach(file_part)
                    f.seek(0)

            with smtplib.SMTP(config["gmail"]["smtp_host"], config["gmail"]["smtp_port"]) as server:
                server.starttls()
                server.login(sender, config["gmail"]["app_password"])
                server.sendmail(sender, to_email, msg.as_string())
        except Exception as e:
            raise CommunicationError(f"SMTP delivery infrastructure malfunction: {str(e)}")

    @staticmethod
    def dispatch_confirmation(
        to_email, company, event_title, date_str, time_str, event_type,
        join_link="", tz_name="Asia/Kolkata"
    ):
        """Sends Registration Confirmed email + .ics calendar invite + Joining Link after registration."""
        config = SystemConfig.validate_and_load()
        sender = config["gmail"]["username"]
        title_display = event_title or f"{company} Programme"

        try:
            local_tz = ZoneInfo(tz_name)
            naive_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            aware_dt = naive_dt.replace(tzinfo=local_tz)
            tz_abbr = aware_dt.strftime("%Z")
            display_time = f"{time_str} {tz_abbr} ({tz_name})"

            msg = MIMEMultipart('mixed')
            msg['Subject'] = f"Registration confirmed for {title_display}"
            msg['From'] = f'"{company}" <{sender}>'
            msg['To'] = to_email

            join_section = ""
            if join_link:
                join_section = f"""
                <div style="background:#f0fdf4; border:1px solid #86efac; border-radius:8px; padding:16px; margin:20px 0;">
                    <p style="margin:0 0 6px 0; font-size:13px; color:#166534; font-weight:bold;">EVENT ACCESS / JOINING LINK</p>
                    <a href="{join_link}" style="font-size:15px; color:#15803d; font-weight:bold; word-break:break-all;">{join_link}</a>
                </div>
                """

            confirm_html = f"""
            <!DOCTYPE html>
            <html>
            <body style="font-family: Arial, sans-serif; background-color: #f8fafc; padding: 24px; color: #1e293b;">
              <div style="max-width: 560px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden;">
                <div style="background: #0f172a; color: #ffffff; padding: 20px 28px;">
                  <p style="margin:0; font-size:13px; opacity:0.85;">{company}</p>
                  <h2 style="margin:6px 0 0 0; font-size:20px;">You have registered for {title_display}</h2>
                </div>
                <div style="padding: 28px;">
                  <p style="margin:0 0 12px 0; font-size:15px;">📅 <strong>Date:</strong> {date_str}</p>
                  <p style="margin:0 0 12px 0; font-size:15px;">🕒 <strong>Time:</strong> {display_time}</p>
                  <p style="margin:0 0 16px 0; font-size:15px;">📍 <strong>Format:</strong> {event_type}</p>
                  {join_section}
                  <p style="font-size:13px; color:#64748b; margin-top:20px;">
                    An <strong>.ics calendar invite</strong> is attached to this email—click <strong>Add to calendar</strong> above to save it to your schedule.
                  </p>
                </div>
                <div style="background:#f1f5f9; padding:14px 28px; text-align:center; font-size:11px; color:#64748b;">
                  POWERED BY UTTARAM EVENT ENGINE
                </div>
              </div>
            </body>
            </html>
            """
            msg.attach(MIMEText(confirm_html, 'html'))

            # Generate .ics calendar invite with joining link in location/description
            c = Calendar()
            e = Event(
                name=title_display,
                begin=aware_dt,
                end=aware_dt + timedelta(hours=1),
                location=join_link or event_type,
                description=f"Hosted by {company}\nJoin Link: {join_link}" if join_link else f"Hosted by {company}"
            )
            c.events.add(e)

            cal_part = MIMEBase('text', 'calendar', method='REQUEST', name='invite.ics')
            cal_part.set_payload(str(c))
            encode_base64(cal_part)
            cal_part.add_header('Content-Disposition', 'attachment; filename="invite.ics"')
            msg.attach(cal_part)

            with smtplib.SMTP(config["gmail"]["smtp_host"], config["gmail"]["smtp_port"]) as server:
                server.starttls()
                server.login(sender, config["gmail"]["app_password"])
                server.sendmail(sender, to_email, msg.as_string())
        except Exception as e:
            raise CommunicationError(f"Confirmation dispatch failed: {str(e)}")
