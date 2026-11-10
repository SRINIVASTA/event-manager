import streamlit as st
from src.core.exceptions import ConfigurationError

class SystemConfig:
    @staticmethod
    def validate_and_load():
        """Unified configuration loader aligned with [gmail] username/app_password secrets."""
        try:
            # Matches your working script: reads st.secrets["gmail"]["username"] directly
            gmail_username = st.secrets["gmail"]["username"]
            gmail_app_password = st.secrets["gmail"]["app_password"]

            # Automatically convert string literal '\n' into true system line breaks
            raw_private_key = st.secrets["gcp_service_account"]["private_key"]
            clean_private_key = raw_private_key.replace("\\n", "\n").replace(r"\n", "\n").strip()

            return {
                "host_email": gmail_username,
                "spreadsheet_id": st.secrets.get("spreadsheet_id", "17dOnyfFGfBGytQXS7SU7fnx6svAyeGKKagGI3OJM4ms"),
                "gmail": {
                    "smtp_host": "smtp.gmail.com",
                    "smtp_port": 587,
                    "imap_host": "imap.gmail.com",
                    "imap_port": 993,
                    "username": gmail_username,
                    "app_password": gmail_app_password
                },
                "gcp_service_account": {
                    "type": "service_account",
                    "project_id": st.secrets["gcp_service_account"]["project_id"],
                    "private_key_id": st.secrets["gcp_service_account"]["private_key_id"],
                    "private_key": clean_private_key,
                    "client_email": st.secrets["gcp_service_account"]["client_email"],
                    "auth_uri": st.secrets["gcp_service_account"]["auth_uri"],
                    "token_uri": st.secrets["gcp_service_account"]["token_uri"],
                    "auth_provider_x509_cert_url": st.secrets["gcp_service_account"]["auth_provider_x509_cert_url"]
                }
            }
        except KeyError as e:
            raise ConfigurationError(
                f"Missing critical production secret field: {str(e)}. "
                "Verify your Streamlit Cloud Secrets dashboard configuration."
            )
