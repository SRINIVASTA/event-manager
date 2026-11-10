import streamlit as st
from src.core.exceptions import ConfigurationError

class SystemConfig:
    @staticmethod
    def validate_and_load():
        """Loads variable parameters from secrets while hardcoding constant Gmail network endpoints."""
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
                "gcp_service_account": dict(st.secrets["gcp_service_account"])
            }
        except KeyError as e:
            raise ConfigurationError(
                f"Missing critical production secret field: {str(e)}. "
                "Verify your Streamlit Cloud Secrets dashboard panel configuration."
            )
