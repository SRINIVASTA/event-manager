import gspread
from src.core.config import SystemConfig
from src.core.exceptions import DatabaseError
from datetime import datetime

class GSheetsDatabase:
    @staticmethod
    def _get_client(config):
        try:
            service_account_info = {
                "type": "service_account",
                "project_id": config["gcp_service_account"]["project_id"],
                "private_key_id": config["gcp_service_account"]["private_key_id"],
                "private_key": config["gcp_service_account"]["private_key"],
                "client_email": config["gcp_service_account"]["client_email"],
                "auth_uri": config["gcp_service_account"]["auth_uri"],
                "token_uri": config["gcp_service_account"]["token_uri"],
                "auth_provider_x509_cert_url": config["gcp_service_account"]["auth_provider_x509_cert_url"]
            }
            return gspread.service_account_from_dict(service_account_info)
        except Exception as e:
            raise DatabaseError(f"Authentication with Google Cloud APIs broken: {str(e)}")

    @staticmethod
    def get_or_create_worksheet(company, date_str, time_str, event_type):
        config = SystemConfig.validate_and_load()
        client = GSheetsDatabase._get_client(config)
        
        spreadsheet_name = f"Event_Records_{company}"
        safe_time = time_str.replace(':', '-')
        tab_name = f"{date_str}_{safe_time}_{event_type.lower()}"

        try:
            # 🚀 ROOT INCEPTION ACTION: Create the file in root workspace to avoid 403 Parent errors completely
            try:
                spreadsheet = client.open(spreadsheet_name)
            except gspread.SpreadsheetNotFound:
                spreadsheet = client.create(spreadsheet_name)
                # Automatically grant full writer privileges to your personal account email
                spreadsheet.share(config["host_email"], perm_type='user', role='writer')

            try:
                worksheet = spreadsheet.worksheet(tab_name)
            except gspread.WorksheetNotFound:
                worksheet = spreadsheet.add_worksheet(title=tab_name, rows="1000", cols="3")
                worksheet.append_row(["Email", "RSVP_Status", "Last_Updated"])
            
            return worksheet
            
        except Exception as e:
            raise DatabaseError(f"Failed to query or create cloud datatable layouts: {str(e)}")

    @staticmethod
    def write_participant_state(company, date_str, time_str, event_type, email, status):
        try:
            worksheet = GSheetsDatabase.get_or_create_worksheet(company, date_str, time_str, event_type)
            records = worksheet.get_all_records()
            now = datetime.now().isoformat()

            for idx, row in enumerate(records, start=2):
                if row['Email'].strip().lower() == email.strip().lower():
                    worksheet.update_cell(idx, 2, status.upper())
                    worksheet.update_cell(idx, 3, now)
                    return

            worksheet.append_row([email.strip().lower(), status.upper(), now])
        except Exception as e:
            raise DatabaseError(f"Could not mutate participant state line entries: {str(e)}")
