import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.encoders import encode_base64
from ics import Calendar, Event
from src.core.config import SystemConfig
from src.core.exceptions import CommunicationError

class GmailDispatcher:
    @staticmethod
    def dispatch_invite(to_email, company, date_str, time_str, event_type, uploaded_files=None):
        config = SystemConfig.validate_and_load()
        sender = config["gmail"]["username"]

        try:
            msg = MIMEMultipart('mixed')
            msg['Subject'] = f"Invitation: {company} Programme ({date_str})"
            msg['From'] = f'"Programmes Portal" <{sender}>'
            msg['To'] = to_email

            # Format structural mailto loops
            metadata = f"| {company} | {date_str} | {time_str} | {event_type}"
            accept_url = f"mailto:{sender}?subject=RSVP ACCEPT {metadata}&body=Send to confirm attendance."
            decline_url = f"mailto:{sender}?subject=RSVP DECLINE {metadata}&body=Send to decline invitation."

            # Inject template path context
            template_path = os.path.join(os.path.dirname(__file__), '../templates/invite_template.html')
            with open(template_path, 'r') as file:
                html_body = file.read()

            html_body = html_body.replace("{{COMPANY_NAME}}", company)\
                                 .replace("{{DATE}}", date_str)\
                                 .replace("{{TIME}}", time_str)\
                                 .replace("{{TYPE}}", event_type)\
                                 .replace("{{ACCEPT_LINK}}", accept_url)\
                                 .replace("{{DECLINE_LINK}}", decline_url)
            
            msg.attach(MIMEText(html_body, 'html'))

            # Attach auto-generated .ics calendar invite payload structural frameworks
            c = Calendar()
            e = Event(name=f"{company} Programme ({event_type})", begin=f"{date_str} {time_str}:00")
            c.events.add(e)
            
            cal_part = MIMEBase('text', 'calendar', method='REQUEST', name='invite.ics')
            cal_part.set_payload(str(c))
            encode_base64(cal_part)
            cal_part.add_header('Content-Disposition', 'attachment; filename="invite.ics"')
            msg.attach(cal_part)

            # Process custom attached assets from form layouts smoothly
            if uploaded_files:
                for f in uploaded_files:
                    file_part = MIMEBase('application', 'octet-stream')
                    file_part.set_payload(f.read())
                    encode_base64(file_part)
                    file_part.add_header('Content-Disposition', f'attachment; filename="{f.name}"')
                    msg.attach(file_part)
                    f.seek(0)

            # Execution block mapping over safe ports
            with smtplib.SMTP(config["gmail"]["smtp_host"], config["gmail"]["smtp_port"]) as server:
                server.starttls()
                server.login(sender, config["gmail"]["app_password"])
                server.sendmail(sender, to_email, msg.as_string())
        except Exception as e:
            raise CommunicationError(f"SMTP delivery infrastructure malfunction code: {str(e)}")
