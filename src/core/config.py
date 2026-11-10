import streamlit as st
from src.core.exceptions import ConfigurationError

class SystemConfig:
    @staticmethod
    def validate_and_load():
        """Ensures all required enterprise credentials live inside the cloud backend environment."""
        try:
            return {
                "host_email": st.secrets["host_email"],
                "gmail": {
                    "smtp_host": st.secrets["gmail"]["smtp_host"],
                    "smtp_port": int(st.secrets["gmail"]["smtp_port"]),
                    "imap_host": st.secrets["gmail"]["imap_host"],
                    "imap_port": int(st.secrets["gmail"]["imap_port"]),
                    "username": st.secrets["gmail"]["username"],
                    "app_password": st.secrets["gmail"]["app_password"]
                },
                "gcp_service_account": dict(st.secrets["gcp_service_account"])
            }
        except KeyError as e:
            raise ConfigurationError(
                f"Missing critical production secret field key mapping: {str(e)}. "
                "Ensure your Streamlit Cloud Advanced Settings panel parameters are correctly configured."
            )
