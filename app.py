import streamlit as st
import pandas as pd
import time
import datetime
from urllib.parse import urlencode
from zoneinfo import ZoneInfo
from src.core.config import SystemConfig
from src.services.gsheets_database import GSheetsDatabase
from src.services.gmail_dispatcher import GmailDispatcher
from src.services.gmail_listener import GmailListener
from src.core.exceptions import EventManagerException

st.set_page_config(
    page_title="Uttaram — Event Communications Engine",
    page_icon="✉️",
    layout="wide",
    initial_sidebar_state="expanded"
)

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

def get_metadata_worksheet():
    ws = GSheetsDatabase.get_or_create_worksheet("Campaigns", "Metadata", "00-00", "Config")
    expected_headers = [
        "campaign_id", "company", "host_name", "event_title", "date_str",
        "time_str", "event_type", "tz_name", "about_event", "cover_url",
        "join_link", "reg_mode", "google_form_url", "form_sheet_tab"
    ]
    if ws.row_values(1) != expected_headers:
        ws.clear()
        ws.append_row(expected_headers)
    return ws

def save_campaign_metadata(meta: dict):
    ws = get_metadata_worksheet()
    row_values = [
        meta["campaign_id"], meta["company"], meta["host_name"], meta["event_title"],
        meta["date_str"], meta["time_str"], meta["event_type"], meta["tz_name"],
        meta["about_event"], meta["cover_url"], meta["join_link"], meta["reg_mode"],
        meta["google_form_url"], meta["form_sheet_tab"]
    ]
    for idx, rec in enumerate(ws.get_all_records(), start=2):
        if str(rec.get("campaign_id")) == meta["campaign_id"]:
            ws.update(f"A{idx}:N{idx}", [row_values])
            return
    ws.append_row(row_values)

def load_campaign_metadata(campaign_id: str) -> dict | None:
    for rec in get_metadata_worksheet().get_all_records():
        if str(rec.get("campaign_id")) == campaign_id:
            return rec
    return None

def sync_google_form_responses(meta: dict, default_tz: str) -> int:
    form_tab = meta.get("form_sheet_tab", "").strip()
    if not form_tab:
        return 0
    try:
        client = GSheetsDatabase._get_client()
        sheet = client.open_by_key(SystemConfig.GOOGLE_SHEET_ID)
        form_rows = sheet.worksheet(form_tab).get_all_records()

        submitted_emails = {
            str(v).strip().lower()
            for r in form_rows for k, v in r.items()
            if "email" in str(k).lower() and "@" in str(v)
        }
        if not submitted_emails:
            return 0

        roster_ws = GSheetsDatabase.get_or_create_worksheet(
            meta["company"], meta["date_str"], meta["time_str"], meta["event_type"]
        )
        updated = 0
        for rec in roster_ws.get_all_records():
            email = str(rec.get("Email", "")).strip().lower()
            if email in submitted_emails and str(rec.get("RSVP_Status", "")).upper() != "ACCEPTED":
                GSheetsDatabase.write_participant_state(
                    meta["company"], meta["date_str"], meta["time_str"],
                    meta["event_type"], email, "ACCEPTED", tz_name=default_tz
                )
                if hasattr(GmailDispatcher, "dispatch_confirmation"):
                    GmailDispatcher.dispatch_confirmation(
                        email, meta["company"], meta["event_title"],
                        meta["date_str"], meta["time_str"], meta["event_type"],
                        meta["join_link"], tz_name=meta.get("tz_name", default_tz)
                    )
                updated += 1
        return updated
    except Exception:
        return 0

event_param = st.query_params.get("event", None)
if event_param:
    st.markdown(
        """
        <style>
            [data-testid="stSidebar"], [data-testid="collapsedControl"] {display: none;}
            .youre-in-box {
                background: #ecfdf5; border: 1px solid #10b981; border-radius: 12px;
                padding: 24px; text-align: center; color: #065f46;
            }
        </style>
        """,
        unsafe_allow_html=True
    )

    meta = load_campaign_metadata(event_param)
    if not meta:
        st.error("Event not found or the invitation link has expired.")
        st.stop()

    guest_email_prefill = st.query_params.get("email", "")
    if meta.get("reg_mode") == "GOOGLE_FORM":
        sync_google_form_responses(meta, meta.get("tz_name", "Asia/Kolkata"))

    roster_records = GSheetsDatabase.get_or_create_worksheet(
        meta["company"], meta["date_str"], meta["time_str"], meta["event_type"]
    ).get_all_records()
    going_count = sum(1 for r in roster_records if str(r.get("RSVP_Status")).upper() == "ACCEPTED")

    guest_status = "PENDING"
    for r in roster_records:
        if guest_email_prefill and str(r.get("Email", "")).strip().lower() == guest_email_prefill.strip().lower():
            guest_status = str(r.get("RSVP_Status", "PENDING")).upper()
            break

    left_col, right_col = st.columns([1, 1.4], gap="large")
    with left_col:
        if meta.get("cover_url"):
            st.image(meta["cover_url"], use_container_width=True)
        else:
            st.info(f"🏢 **{meta['company']}**")
        st.markdown(f"**Presented by**\n### {meta['company']}")
        st.markdown(f"**Hosted By**\n👤 {meta['host_name']}")
        st.divider()
        st.metric("Attendees Confirmed", f"{going_count} Going")

    with right_col:
        st.title(meta["event_title"])
        st.markdown(f"📅 **{meta['date_str']}** | 🕒 **{meta['time_str']} ({meta['tz_name']})** | 📍 **{meta['event_type']}**")
        st.divider()

        if guest_status == "ACCEPTED" or st.session_state.get("just_accepted"):
            st.markdown(
                """
                <div class="youre-in-box">
                    <h2 style="margin:0;">✓ You’re In</h2>
                    <p style="font-size:16px; margin-top:8px;">Thank you. We look forward to seeing you!</p>
                </div>
                """,
                unsafe_allow_html=True
            )
            st.success("Registration confirmed! A calendar invite (.ics) and joining details have been sent to your email.")
            if meta.get("join_link"):
                st.info(f"🔗 **Event Access / Location:** {meta['join_link']}")
        elif guest_status == "DECLINED":
            st.warning("You have declined this invitation.")
        else:
            st.subheader("Registration")
            st.write(f"You are invited by **{meta['host_name']}** ({meta['company']}). Please register below.")

            if meta.get("reg_mode") == "BUILTIN":
                with st.form("builtin_rsvp_form"):
                    guest_name = st.text_input("Name *", placeholder="Enter your full name")
                    guest_email = st.text_input("Email *", value=guest_email_prefill, placeholder="you@example.com")
                    c1, c2 = st.columns(2)
                    acc = c1.form_submit_button("✅ Accept Invite", type="primary", use_container_width=True)
                    dec = c2.form_submit_button("❌ Decline", use_container_width=True)

                    if acc:
                        if not guest_name.strip() or "@" not in guest_email:
                            st.error("Please enter both your Name and a valid Email.")
                        else:
                            GSheetsDatabase.write_participant_state(
                                meta["company"], meta["date_str"], meta["time_str"],
                                meta["event_type"], guest_email.strip(), "ACCEPTED", tz_name=meta["tz_name"]
                            )
                            if hasattr(GmailDispatcher, "dispatch_confirmation"):
                                GmailDispatcher.dispatch_confirmation(
                                    guest_email.strip(), meta["company"], meta["event_title"],
                                    meta["date_str"], meta["time_str"], meta["event_type"],
                                    meta["join_link"], tz_name=meta["tz_name"]
                                )
                            st.session_state["just_accepted"] = True
                            st.rerun()
                    if dec and "@" in guest_email:
                        GSheetsDatabase.write_participant_state(
                            meta["company"], meta["date_str"], meta["time_str"],
                            meta["event_type"], guest_email.strip(), "DECLINED", tz_name=meta["tz_name"]
                        )
                        st.rerun()
            else:
                c1, c2 = st.columns(2)
                c1.link_button("📝 Accept Invite & Fill Form", url=meta.get("google_form_url", ""), type="primary", use_container_width=True)
                if c2.button("❌ Decline Invite", use_container_width=True) and guest_email_prefill:
                    GSheetsDatabase.write_participant_state(
                        meta["company"], meta["date_str"], meta["time_str"],
                        meta["event_type"], guest_email_prefill, "DECLINED", tz_name=meta["tz_name"]
                    )
                    st.rerun()
                if st.button("🔄 Refresh Registration Status"):
                    sync_google_form_responses(meta, meta["tz_name"])
                    st.rerun()

        st.divider()
        st.subheader("About Event")
        st.markdown(meta.get("about_event", ""))
    st.stop()
elif selected_page == "📊 Cloud Database Roster Tracker":
    st.subheader("📊 Google Sheets Synchronization & Roster Visualiser")
    st.markdown("Click **Sync & Pull Roster** to fetch new Gmail replies, sync Google Form responses, and view live attendance.")

    c1, c2, c3, c4 = st.columns(4)
    sc = c1.text_input("Filter Company Name Key:", value="infosys")
    sd = c2.text_input("Filter Date Matrix (YYYY-MM-DD):", value=current_local_now.strftime("%Y-%m-%d"))
    st_t = c3.text_input("Filter Time String (HH:MM):", value="14:30")
    sty = c4.selectbox("Filter Operational Type Map:", ["Virtual", "Walk-in"])

    if st.button("🔄 Sync Inbox, Forms & Pull Roster Sheet Data", type="primary"):
        with st.spinner("Syncing Gmail RSVPs, Google Form submissions & loading Roster..."):
            try:
                logs = GmailListener.poll_and_sync_rsvps(default_tz=active_tz)
                if logs:
                    for log_entry in logs:
                        st.toast(log_entry, icon="✅")
                    st.success(f"Inbox synced! Processed {len(logs)} email RSVP response(s).")

                campaign_id = f"{sc.strip().lower().replace(' ', '_')}_{sd}_{st_t.replace(':', '-')}_{sty.lower()}"
                meta = load_campaign_metadata(campaign_id)
                if meta and meta.get("reg_mode") == "GOOGLE_FORM":
                    form_updates = sync_google_form_responses(meta, active_tz)
                    if form_updates > 0:
                        st.success(f"Google Form synced! Confirmed {form_updates} new registration(s).")

                worksheet = GSheetsDatabase.get_or_create_worksheet(sc, sd, st_t, sty)
                raw_matrix = worksheet.get_all_records()

                if raw_matrix:
                    dataframe = pd.DataFrame(raw_matrix)

                    total_accepted = len(dataframe[dataframe['RSVP_Status'] == 'ACCEPTED'])
                    total_pending = len(dataframe[dataframe['RSVP_Status'] == 'PENDING'])
                    total_declined = len(dataframe[dataframe['RSVP_Status'] == 'DECLINED'])

                    metric_col1, metric_col2, metric_col3 = st.columns(3)
                    metric_col1.metric("✅ Confirmed Accepted", total_accepted)
                    metric_col2.metric("⏳ Pending Responses", total_pending)
                    metric_col3.metric("❌ Declined", total_declined)

                    st.dataframe(dataframe, use_container_width=True)
                else:
                    st.warning("Spreadsheet tab mapped accurately, but row data is currently empty.")
            except EventManagerException as error:
                st.error(f"Failed to sync or extract roster data: {str(error)}")
