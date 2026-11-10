import streamlit as st
import pandas as pd
import time
import datetime
from zoneinfo import ZoneInfo
from src.core.config import SystemConfig
from src.services.gsheets_database import GSheetsDatabase
from src.services.gmail_dispatcher import GmailDispatcher
from src.services.gmail_listener import GmailListener
from src.core.exceptions import EventManagerException

try:
    SystemConfig.validate_and_load()
except EventManagerException as e:
    st.error(str(e))
    st.stop()

TIMEZONE_OPTIONS = {
    "India (IST - Asia/Kolkata)": "Asia/Kolkata",
    "USA Eastern (EST/EDT - America/New_York)": "America/New_York",
    "USA Central (CST/CDT - America/Chicago)": "America/Chicago",
    "USA Mountain (MST/MDT - America/Denver)": "America/Denver",
    "USA Pacific (PST/PDT - America/Los_Angeles)": "America/Los_Angeles",
    "UK (GMT/BST - Europe/London)": "Europe/London",
    "UAE (GST - Asia/Dubai)": "Asia/Dubai",
    "Singapore (SGT - Asia/Singapore)": "Asia/Singapore",
    "Australia Sydney (AEST/AEDT - Australia/Sydney)": "Australia/Sydney",
    "UTC (Universal Coordinated Time)": "UTC"
}

st.title("✉️ Enterprise Event Communications Engine")
st.markdown("Automate Luma-style templates, secure dynamic attachments, and synchronize tracking lists live to Google Sheets via Gmail APIs.")

# Global Region / Timezone Selector at the top of the app
selected_tz_label = st.selectbox(
    "🌍 Select Active Region / Timezone (applies to invites, calendar files & sheet logs):",
    options=list(TIMEZONE_OPTIONS.keys()),
    index=0  # Defaults to India (Asia/Kolkata)
)
active_tz = TIMEZONE_OPTIONS[selected_tz_label]
current_local_now = datetime.datetime.now(ZoneInfo(active_tz))
st.caption(f"Current local time in selected region: **{current_local_now.strftime('%Y-%m-%d %H:%M:%S %Z')}**")

tab_dispatch, tab_analytics = st.tabs(["🆕 Launch Campaign Portal", "📊 Cloud Database Roster Tracker"])

with tab_dispatch:
    st.subheader("Initialise Program Communications Configuration Parameters")
    
    col_left, col_right = st.columns(2)
    with col_left:
        company = st.text_input("Target Corporate/Program entity Name:", placeholder="e.g., Infosys")
        event_date = st.date_input("Target Execution Date Frame:", value=current_local_now.date())
        event_time = st.time_input("Target Execution Timestamp Layout:", value=datetime.time(14, 30))
    with col_right:
        event_type = st.selectbox("Select Access Medium Format Typer Matrix:", ["Virtual", "Walk-in"])
        receivers_input = st.text_area("Input Intended Recipient Email List Strings (separate items by commas or separate lines):")

    uploaded_files = st.file_uploader("Upload additional supporting text assets/materials documents directly", accept_multiple_files=True)

    if st.button("🚀 Authorise Workspace & Send Invitations"):
        if not company or not receivers_input:
            st.error("Please fill in both the Company Name and provide valid Recipient Email inputs.")
            st.stop()

        try:
            raw_tokens = receivers_input.replace("\n", ",").split(",")
            clean_recipients = [r.strip() for r in raw_tokens if "@" in r]

            d_str = event_date.strftime("%Y-%m-%d")
            t_str = event_time.strftime("%H:%M")

            GSheetsDatabase.get_or_create_worksheet(company, d_str, t_str, event_type)

            ui_progress = st.progress(0)
            ui_status = st.empty()

            for index, recipient in enumerate(clean_recipients):
                ui_status.text(f"Processing structural registration pipeline state allocations mapping for: {recipient}")
                
                GSheetsDatabase.write_participant_state(
                    company, d_str, t_str, event_type, recipient, "PENDING", tz_name=active_tz
                )
                
                GmailDispatcher.dispatch_invite(
                    recipient, company, d_str, t_str, event_type, uploaded_files, tz_name=active_tz
                )
                
                ui_progress.progress((index + 1) / len(clean_recipients))
                if len(clean_recipients) > 1:
                    time.sleep(1.0)

            ui_status.empty()
            st.success(f"Successfully deployed communications grid in {active_tz}. {len(clean_recipients)} Luma templates sent out successfully! 🚀")

        except EventManagerException as error:
            st.error(f"Application flow interruption fault caught: {str(error)}")

with tab_analytics:
    st.subheader("Google Sheets Synchronization Controls Hub")
    
    if st.button("🔄 Sync Inbound RSVP Responses From Inbox Now"):
        with st.spinner("Connecting to Gmail secure messaging IMAP server loops configuration framework..."):
            try:
                logs = GmailListener.poll_and_sync_rsvps(default_tz=active_tz)
                if logs:
                    for log_entry in logs:
                        st.toast(log_entry, icon="✅")
                    st.success(f"Synchronisation complete! Synced {len(logs)} participant status adjustments.")
                else:
                    st.info("No unread email RSVP confirmations detected in the system inbox at this time.")
            except EventManagerException as error:
                st.error(f"Sync operation failure message parameters: {str(error)}")

    st.divider()
    st.markdown("### Inspect Cloud Document Workspace Tab Visualiser Dataframes")
    
    c1, c2, c3, c4 = st.columns(4)
    sc = c1.text_input("Filter Company Name Key:", value="infosys")
    sd = c2.text_input("Filter Date Matrix (YYYY-MM-DD):", value=current_local_now.strftime("%Y-%m-%d"))
    st_t = c3.text_input("Filter Time String (HH:MM):", value="14:30")
    sty = c4.selectbox("Filter Operational Type Map:", ["Virtual", "Walk-in"])

    if st.button("🔍 Pull Roster Sheet Data Matrix"):
        try:
            worksheet = GSheetsDatabase.get_or_create_worksheet(sc, sd, st_t, sty)
            raw_matrix = worksheet.get_all_records()
            
            if raw_matrix:
                dataframe = pd.DataFrame(raw_matrix)
                st.dataframe(dataframe, use_container_width=True)
                
                total_accepted = len(dataframe[dataframe['RSVP_Status'] == 'ACCEPTED'])
                total_pending = len(dataframe[dataframe['RSVP_Status'] == 'PENDING'])
                
                metric_col1, metric_col2 = st.columns(2)
                metric_col1.metric("Confirmed Accepted Attendees count", total_accepted)
                metric_col2.metric("Remaining Pending responses tracker status", total_pending)
            else:
                st.warning("Spreadsheet schema database tab mapped accurately, but row elements data is currently empty.")
        except EventManagerException as error:
            st.error(f"Failed to extract matching target cloud documents view parameters structure: {str(error)}")
