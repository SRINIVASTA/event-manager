import imaplib
import email
from email.header import decode_header
from src.core.config import SystemConfig
from src.core.exceptions import CommunicationError
from src.services.gsheets_database import GSheetsDatabase

class GmailListener:
    @staticmethod
    def _decode_subject(raw_subject):
        if not raw_subject:
            return ""
        decoded_parts = decode_header(raw_subject)
        subject = ""
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                subject += part.decode(encoding or "utf-8", errors="ignore")
            else:
                subject += part
        return subject

    @staticmethod
    def poll_and_sync_rsvps(default_tz="Asia/Kolkata"):
        config = SystemConfig.validate_and_load()
        sync_logs = []

        try:
            mail = imaplib.IMAP4_SSL(config["gmail"]["imap_host"], config["gmail"]["imap_port"])
            mail.login(config["gmail"]["username"], config["gmail"]["app_password"])
            mail.select("inbox")

            status, response = mail.search(None, '(UNSEEN SUBJECT "RSVP ")')
            if status == 'OK' and response and response[0]:
                for num in response[0].split():
                    status, data = mail.fetch(num, '(RFC822)')
                    if status != 'OK' or not data or not data[0]:
                        continue
                    
                    msg = email.message_from_bytes(data[0][1])
                    subject = GmailListener._decode_subject(msg['Subject'])
                    sender_raw = email.utils.parseaddr(msg['From'])[1]

                    if "RSVP " in subject and "|" in subject:
                        parts = [p.strip() for p in subject.split('|')]
                        if len(parts) >= 5:
                            action = "ACCEPTED" if "ACCEPT" in parts[0].upper() else "DECLINED"
                            company = parts[1]
                            date_str = parts[2]
                            time_str = parts[3]
                            event_type = parts[4]
                            tz_name = parts[5] if len(parts) >= 6 else default_tz

                            GSheetsDatabase.write_participant_state(
                                company, date_str, time_str, event_type, sender_raw, action, tz_name=tz_name
                            )
                            sync_logs.append(f"Synchronised {sender_raw} -> {action} ({company})")
                            mail.store(num, '+FLAGS', '\\Seen')

            mail.logout()
            return sync_logs
        except Exception as e:
            raise CommunicationError(f"IMAP extraction engine network failure: {str(e)}")
