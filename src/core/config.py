import streamlit as st
from src.core.exceptions import ConfigurationError

class SystemConfig:
    @staticmethod
    def validate_and_load():
        """Secure single source of truth loading credentials from Streamlit Secrets with strict Google OAuth URLs."""
        try:
            return {
                "host_email": st.secrets["host_email"],
                "gmail": {
                    "smtp_host": "smtp.gmail.com",
                    "smtp_port": 587,
                    "imap_host": "imap.gmail.com",
                    "imap_port": 993,
                    "username": st.secrets["gmail"]["username"],
                    "app_password": st.secrets["gmail"]["app_password"]
                },
                "gcp_service_account": {
                    "type": "service_account",
                    "project_id": "gen-lang-client-0447660309",
                    "private_key_id": st.secrets["gcp_service_account"]["private_key_id"],
                    "private_key": st.secrets["gcp_service_account"]["private_key"],
                    "client_email": st.secrets["gcp_service_account"]["client_email"],
                    # EXACT FIXED ENDPOINTS: Explicitly required by Google OAuth Client
                    "auth_uri": "https://google.com",
                    "token_uri": "https://googleapis.com",
                    "auth_provider_x509_cert_url": "https://googleapis.com"
                }
            }
        except KeyError as e:
            raise ConfigurationError(
                f"Missing critical production secret field: {str(e)}. "
                "Verify your Streamlit Cloud Secrets dashboard panel configuration."
            )
