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
        
        safe_time = time_str.replace(':', '-')
        # Formats tab dynamically inside your master spreadsheet: e.g., infosys_2026-11-10_14-30_virtual
        tab_name = f"{company}_{date_str}_{safe_time}_{event_type.lower()}"

        # 🚀 REWRITE FIX: HARDCODE THE EXACT UNIQUE SPREADSHEET URL ID
        # Replace the characters below with the exact ID from your browser address bar link!
        spreadsheet_id = "PASTE_YOUR_LONG_SPREADSHEET_ID_HERE"

        try:
            # Connect directly to the specific sheet using its ID to dodge case-sensitivity bugs entirely
            try:
                spreadsheet = client.open_by_key(spreadsheet_id)
            except gspread.SpreadsheetNotFound:
                raise DatabaseError(
                    f"Spreadsheet key ID '{spreadsheet_id}' could not be accessed! "
                    f"Ensure you shared the file with this service email as Editor: "
                    f"{config['gcp_service_account']['client_email']}"
                )

            # Programmatically provision and structure individual tracker tabs
            try:
                worksheet = spreadsheet.worksheet(tab_name)
            except gspread.WorksheetNotFound:
                worksheet = spreadsheet.add_worksheet(title=tab_name, rows="1000", cols="3")
                worksheet.append_row(["Email", "RSVP_Status", "Last_Updated"])
            
            return worksheet
        except Exception as e:
            raise DatabaseError(f"Failed to manage master cloud datatable layouts: {str(e)}")

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
