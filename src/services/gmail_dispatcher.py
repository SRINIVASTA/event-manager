import smtplib
import os
from datetime import datetime
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
    def dispatch_invite(to_email, company, date_str, time_str, event_type, uploaded_files=None, tz_name="Asia/Kolkata"):
        config = SystemConfig.validate_and_load()
        sender = config["gmail"]["username"]

        try:
            # Build timezone-aware start datetime (handles India IST, USA EST/PST, etc. automatically)
            local_tz = ZoneInfo(tz_name)
            naive_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            aware_dt = naive_dt.replace(tzinfo=local_tz)
            tz_abbr = aware_dt.strftime("%Z")  # e.g., 'IST', 'EST', 'PST', 'GMT'
            display_time = f"{time_str} {tz_abbr} ({tz_name})"

            msg = MIMEMultipart('mixed')
            msg['Subject'] = f"Invitation: {company} Programme ({date_str})"
            msg['From'] = f'"Programmes Portal" <{sender}>'
            msg['To'] = to_email

            # Embed tz_name in metadata so RSVP sync logs the response in the same timezone
            metadata = f"| {company} | {date_str} | {time_str} | {event_type} | {tz_name}"
            accept_subject = quote(f"RSVP ACCEPT {metadata}")
            accept_body = quote("Send this email as-is to confirm your attendance.")
            decline_subject = quote(f"RSVP DECLINE {metadata}")
            decline_body = quote("Send this email as-is to decline the invitation.")

            accept_url = f"mailto:{sender}?subject={accept_subject}&body={accept_body}"
            decline_url = f"mailto:{sender}?subject={decline_subject}&body={decline_body}"

            template_path = os.path.join(os.path.dirname(__file__), '../templates/invite_template.html')
            with open(template_path, 'r', encoding='utf-8') as file:
                html_body = file.read()

            html_body = (
                html_body.replace("{{COMPANY_NAME}}", company)
                         .replace("{{DATE}}", date_str)
                         .replace("{{TIME}}", display_time)
                         .replace("{{TYPE}}", event_type)
                         .replace("{{ACCEPT_LINK}}", accept_url)
                         .replace("{{DECLINE_LINK}}", decline_url)
            )
            
            msg.attach(MIMEText(html_body, 'html'))

            # Generate .ics calendar attachment using the exact timezone-aware datetime
            c = Calendar()
            e = Event(
                name=f"{company} Programme ({event_type})",
                begin=aware_dt
            )
            c.events.add(e)
            
            cal_part = MIMEBase('text', 'calendar', method='REQUEST', name='invite.ics')
            cal_part.set_payload(str(c))
            encode_base64(cal_part)
            cal_part.add_header('Content-Disposition', 'attachment; filename="invite.ics"')
            msg.attach(cal_part)

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
