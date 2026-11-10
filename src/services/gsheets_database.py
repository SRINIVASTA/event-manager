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
        
        # We will use a single master spreadsheet instead of generating multiple files, 
        # which completely dodges the personal Drive quota restriction limit bug.
        spreadsheet_name = "Master_Event_Roster"
        safe_time = time_str.replace(':', '-')
        
        # Each unique event will automatically become its own beautiful separate tab folder inside it!
        tab_name = f"{company}_{date_str}_{safe_time}_{event_type.lower()}"

        try:
            # 🚀 TOML NO-QUOTA STRATEGY: Try opening the master tracker file.
            try:
                spreadsheet = client.open(spreadsheet_name)
            except gspread.SpreadsheetNotFound:
                # If it's the very first run, we let the app attempt a singular base initialization
                try:
                    spreadsheet = client.create(spreadsheet_name)
                    spreadsheet.share(config["host_email"], perm_type='user', role='writer')
                except gspread.exceptions.APIError as e:
                    # If Google strictly locks file creation on this specific developer zone,
                    # we instruct the user on how to resolve it via an alternative approach.
                    raise DatabaseError(
                        f"Google storage limits prevent script file creation. Please go to your personal Google Sheets, "
                        f"create a blank spreadsheet named '{spreadsheet_name}', and click Share to add this email as Editor: "
                        f"{config['gcp_service_account']['client_email']}"
                    )

            # Programmatically provision and structure individual tabs inside the document
            try:
                worksheet = spreadsheet.worksheet(tab_name)
            except gspread.WorksheetNotFound:
                worksheet = spreadsheet.add_worksheet(title=tab_name, rows="1000", cols="3")
                worksheet.append_row(["Email", "RSVP_Status", "Last_Updated"])
            
            return worksheet
        except Exception as e:
            raise DatabaseError(str(e))

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
