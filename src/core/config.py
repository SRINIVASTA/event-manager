import streamlit as st
from src.core.exceptions import ConfigurationError

class SystemConfig:
    @staticmethod
    def validate_and_load():
        """Secure single source of truth loading hardcoded Gmail settings and safe block secrets."""
        try:
            # Safely extract and explicitly force standard literal newline breaks
            raw_key_lines = st.secrets["gcp_service_account"]["private_key_lines"]
            
            # CRITICAL FIX: Explicitly join keys with standard \n character structures
            reconstructed_private_key = "\n".join(raw_key_lines) + "\n"

            account_email = st.secrets["shared_email"]

            return {
                "host_email": account_email,
                "gmail": {
                    "smtp_host": "smtp.gmail.com",
                    "smtp_port": 587,
                    "imap_host": "imap.gmail.com",
                    "imap_port": 993,
                    "username": account_email,
                    "app_password": st.secrets["gmail"]["app_password"]
                },
                "gcp_service_account": {
                    "type": "service_account",
                    "project_id": "gen-lang-client-0447660309",
                    "private_key_id": st.secrets["gcp_service_account"]["private_key_id"],
                    "private_key": reconstructed_private_key,
                    "client_email": st.secrets["gcp_service_account"]["client_email"],
                    "auth_uri": st.secrets["gcp_service_account"]["auth_uri"],
                    "token_uri": st.secrets["gcp_service_account"]["token_uri"],
                    "auth_provider_x509_cert_url": st.secrets["gcp_service_account"]["auth_provider_x509_cert_url"]
                }
            }
        except KeyError as e:
            raise ConfigurationError(
                f"Missing critical production secret field: {str(e)}. "
                "Verify your Streamlit Cloud Secrets dashboard panel configuration."
            )
