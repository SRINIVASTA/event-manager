import imaplib
import email
from src.core.config import SystemConfig
from src.core.exceptions import CommunicationError
from src.services.gsheets_database import GSheetsDatabase

class GmailListener:
    @staticmethod
    def poll_and_sync_rsvps():
        config = SystemConfig.validate_and_load()
        sync_logs = []

        try:
            mail = imaplib.IMAP4_SSL(config["gmail"]["imap_host"], config["gmail"]["imap_port"])
            mail.login(config["gmail"]["username"], config["gmail"]["app_password"])
            mail.select("inbox")

            status, response = mail.search(None, '(UNSEEN SUBJECT "RSVP ")')
            if status == 'OK':
                for num in response.split():
                    status, data = mail.fetch(num, '(RFC822)')
                    if status != 'OK': continue
                    
                    msg = email.message_from_bytes(data[0][1])
                    subject = msg['Subject']
                    sender_raw = email.utils.parseaddr(msg['From'])[1]

                    if "RSVP " in subject and "|" in subject:
                        parts = [p.strip() for p in subject.split('|')]
                        if len(parts) >= 5:
                            action = "ACCEPTED" if "ACCEPT" in parts[0].upper() else "DECLINED"
                            company, date_str, time_str, event_type = parts[1], parts[2], parts[3], parts[4]

                            # Commit structural alignment details to Cloud Spreadsheet
                            GSheetsDatabase.write_participant_state(
                                company, date_str, time_str, event_type, sender_raw, action
                            )
                            sync_logs.append(f"Synchronised {sender_raw} -> {action} ({company})")
                            mail.store(num, '+FLAGS', '\\Seen')

            mail.logout()
            return sync_logs
        except Exception as e:
            raise CommunicationError(f"IMAP extraction engine network failure: {str(e)}")
