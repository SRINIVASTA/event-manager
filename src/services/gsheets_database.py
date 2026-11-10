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
            raise DatabaseError(f"Authentication with Google Cloud APIs broken: {repr(e)}")

    @staticmethod
    def get_or_create_worksheet(company, date_str, time_str, event_type):
        config = SystemConfig.validate_and_load()
        client = GSheetsDatabase._get_client(config)
        
        safe_time = time_str.replace(':', '-')
        tab_name = f"{company}_{date_str}_{safe_time}_{event_type.lower()}"
        spreadsheet_id = "17dOnyfFGfBGytQXS7SU7fnx6svAyeGKKagGI3OJM4ms"

        try:
            try:
                spreadsheet = client.open_by_key(spreadsheet_id)
            except gspread.SpreadsheetNotFound:
                raise DatabaseError(
                    f"Spreadsheet key ID '{spreadsheet_id}' could not be accessed! "
                    f"Ensure you shared the file with this service email as Editor: "
                    f"{config['gcp_service_account']['client_email']}"
                )

            try:
                worksheet = spreadsheet.worksheet(tab_name)
            except gspread.WorksheetNotFound:
                worksheet = spreadsheet.add_worksheet(title=tab_name, rows="1000", cols="3")
                worksheet.append_row(["Email", "RSVP_Status", "Last_Updated"])
            
            return worksheet
        except DatabaseError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to manage master cloud datatable layouts: {repr(e)}")

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
            raise DatabaseError(f"Could not mutate participant state line entries: {repr(e)}")
