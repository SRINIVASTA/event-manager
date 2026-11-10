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
        host_email = config.get("gmail").get("username").strip().lower()
        sync_logs = []

        try:
            mail = imaplib.IMAP4_SSL(
                config.get("gmail").get("imap_host"),
                config.get("gmail").get("imap_port")
            )
            mail.login(
                config.get("gmail").get("username"),
                config.get("gmail").get("app_password")
            )
            mail.select("inbox")

            status, response = mail.search(None, '(SUBJECT "RSVP ")')
            raw_ids = next(iter(response), b"") if status == "OK" and response else b""

            for num in raw_ids.split():
                fetch_status, data = mail.fetch(num, "(RFC822)")
                if fetch_status != "OK" or not data:
                    continue

                first_item = next(iter(data), None)
                if not isinstance(first_item, tuple):
                    continue

                _, raw_email_bytes = first_item
                msg = email.message_from_bytes(raw_email_bytes)
                subject = GmailListener._decode_subject(msg.get("Subject"))

                _, parsed_email = email.utils.parseaddr(msg.get("From"))
                sender_raw = parsed_email.strip().lower()

                if not sender_raw or sender_raw == host_email:
                    continue

                if "RSVP " in subject.upper() and "|" in subject:
                    parts = tuple(p.strip() for p in subject.split("|"))
                    if len(parts) >= 5:
                        action_raw, company, date_str, time_str, event_type, *extra = parts
                        action = "ACCEPTED" if "ACCEPT" in action_raw.upper() else "DECLINED"
                        tz_name = next(iter(extra), default_tz)

                        GSheetsDatabase.write_participant_state(
                            company, date_str, time_str, event_type, sender_raw, action, tz_name=tz_name
                        )
                        sync_logs.append(f"Synchronised {sender_raw} -> {action} ({company})")
                        mail.store(num, "+FLAGS", "\\Seen")

            mail.logout()
            return sync_logs
        except Exception as e:
            raise CommunicationError(f"IMAP extraction engine network failure: {repr(e)}")
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
        host_email = config["gmail"]["username"].strip().lower()
        sync_logs = []

        try:
            mail = imaplib.IMAP4_SSL(config["gmail"]["imap_host"], config["gmail"]["imap_port"])
            mail.login(config["gmail"]["username"], config["gmail"]["app_password"])
            mail.select("inbox")

            status, response = mail.search(None, '(SUBJECT "RSVP ")')
            if status == 'OK' and response and response[0]:
                for num in response[0].split():
                    status, data = mail.fetch(num, '(RFC822)')
                    if status != 'OK' or not data or not data[0]:
                        continue
                    
                    msg = email.message_from_bytes(data[0][1])
                    subject = GmailListener._decode_subject(msg['Subject'])
                    sender_raw = email.utils.parseaddr(msg['From'])[1].strip().lower()

                    if not sender_raw or sender_raw == host_email:
                        continue

                    if "RSVP " in subject.upper() and "|" in subject:
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
