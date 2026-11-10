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
    def poll_and_sync_rsvps():
        config = SystemConfig.validate_and_load()
        sync_logs = []

        try:
            mail = imaplib.IMAP4_SSL(config["gmail"]["imap_host"], config["gmail"]["imap_port"])
            mail.login(config["gmail"]["username"], config["gmail"]["app_password"])
            mail.select("inbox")

            status, response = mail.search(None, '(UNSEEN SUBJECT "RSVP ")')
            if status == 'OK' and response:
                for num in response.split():
                    status, data = mail.fetch(num, '(RFC822)')
                    if status != 'OK':
                        continue
                    
                    msg = email.message_from_bytes(data)
                    subject = GmailListener._decode_subject(msg['Subject'])
                    sender_raw = email.utils.parseaddr(msg['From'])

                    if "RSVP " in subject and "|" in subject:
                        parts = [p.strip() for p in subject.split('|')]
                        if len(parts) >= 5:
                            action = "ACCEPTED" if "ACCEPT" in parts.upper() else "DECLINED"
                            company, date_str, time_str, event_type = parts, parts, parts, parts

                            GSheetsDatabase.write_participant_state(
                                company, date_str, time_str, event_type, sender_raw, action
                            )
                            sync_logs.append(f"Synchronised {sender_raw} -> {action} ({company})")
                            mail.store(num, '+FLAGS', '\\Seen')

            mail.logout()
            return sync_logs
        except Exception as e:
            raise CommunicationError(f"IMAP extraction engine network failure: {str(e)}")
