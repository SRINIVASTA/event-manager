import streamlit as st
import pandas as pd
import time
import datetime
import base64
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
        "join_link", "reg_mode", "custom_questions"
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
        meta["custom_questions"]
    ]
    for idx, rec in enumerate(ws.get_all_records(), start=2):
        if str(rec.get("campaign_id")) == meta["campaign_id"]:
            ws.update(f"A{idx}:M{idx}", [row_values])
            return
    ws.append_row(row_values)

def load_campaign_metadata(campaign_id: str) -> dict | None:
    for rec in get_metadata_worksheet().get_all_records():
        if str(rec.get("campaign_id")) == campaign_id:
            return rec
    return None

def save_guest_registration_details(meta: dict, email: str, guest_name: str, answers: dict):
    """Updates RSVP_Status to ACCEPTED and automatically appends custom question columns."""
    GSheetsDatabase.write_participant_state(
        meta["company"], meta["date_str"], meta["time_str"],
        meta["event_type"], email, "ACCEPTED", tz_name=meta["tz_name"]
    )
    ws = GSheetsDatabase.get_or_create_worksheet(
        meta["company"], meta["date_str"], meta["time_str"], meta["event_type"]
    )
    headers = ws.row_values(1)
    all_fields = {"Guest_Name": guest_name, **answers}

    for field_name in all_fields:
        if field_name not in headers:
            headers.append(field_name)
    ws.update("A1", [headers])

    records = ws.get_all_records()
    for row_idx, rec in enumerate(records, start=2):
        if str(rec.get("Email", "")).strip().lower() == email.strip().lower():
            for field_name, val in all_fields.items():
                col_idx = headers.index(field_name) + 1
                ws.update_cell(row_idx, col_idx, val)
            break

# --- GUEST EVENT & REGISTRATION PORTAL (?event=...) ---
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
            st.success("Registration confirmed! Your details have been recorded.")
            if meta.get("join_link"):
                st.info(f"🔗 **Event Access / Location:** {meta['join_link']}")
        elif guest_status == "DECLINED":
            st.warning("You have declined this invitation.")
        else:
            st.subheader("Registration")
            st.write(f"You are invited by **{meta['host_name']}** ({meta['company']}). Please fill out your details below to accept.")

            raw_q = str(meta.get("custom_questions", "")).strip()
            custom_q_list = [q.strip() for q in raw_q.split(",") if q.strip()] if meta.get("reg_mode") == "CUSTOM_FORM" else []

            with st.form("dynamic_rsvp_form"):
                st.markdown("**Your Info**")
                guest_name = st.text_input("Full Name *", placeholder="Enter your full name")
                guest_email = st.text_input("Email *", value=guest_email_prefill, placeholder="you@example.com")

                custom_answers = {}
                for q_label in custom_q_list:
                    custom_answers[q_label] = st.text_input(f"{q_label} *", placeholder=f"Enter {q_label}")

                c1, c2 = st.columns(2)
                acc = c1.form_submit_button("✅ Accept Invite", type="primary", use_container_width=True)
                dec = c2.form_submit_button("❌ Decline", use_container_width=True)

                if acc:
                    missing_custom = [k for k, v in custom_answers.items() if not v.strip()]
                    if not guest_name.strip() or "@" not in guest_email or missing_custom:
                        st.error("Please fill in all required (*) fields before accepting.")
                    else:
                        save_guest_registration_details(meta, guest_email.strip(), guest_name.strip(), custom_answers)
                        if hasattr(GmailDispatcher, "dispatch_confirmation") and meta.get("join_link"):
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

        st.divider()
        st.subheader("About Event")
        st.markdown(meta.get("about_event", ""))
    st.stop()

with st.sidebar:
    st.title("✉️ Uttaram")
    st.caption("Enterprise Event Communications Engine")
    st.divider()

    selected_page = st.radio(
        "🧭 Workspace Navigation",
        options=["🆕 Launch Campaign Portal", "📊 Cloud Database Roster Tracker"],
        index=0
    )

    st.divider()

    selected_tz_label = st.selectbox(
        "🌍 Active Region / Timezone",
        options=list(TIMEZONE_OPTIONS.keys()),
        index=0
    )
    active_tz = TIMEZONE_OPTIONS[selected_tz_label]
    current_local_now = datetime.datetime.now(ZoneInfo(active_tz))

    st.info(f"🕒 **Local Time:**\n\n`{current_local_now.strftime('%Y-%m-%d %H:%M:%S %Z')}`")
    st.divider()
    st.caption("Powered by Uttaram Event Engine")

st.title("✉️ Uttaram — Enterprise Event Communications Engine")
st.markdown("Automate branded invitations, custom registration workflows, and live RSVP tracking to Google Sheets.")
st.divider()

if selected_page == "🆕 Launch Campaign Portal":
    st.subheader("🆕 Initialise Program Communications Configuration")

    col_left, col_right = st.columns(2)
    with col_left:
        company = st.text_input("Organization / Company Name:", placeholder="e.g., Infosys")
        host_name = st.text_input("Hosted By (Organizer Name):", placeholder="e.g., Srinivas T A")
        event_title = st.text_input("Event Title:", placeholder="e.g., Enterprise AI Agents Workshop")

    with col_right:
        event_date = st.date_input("Target Execution Date:", value=current_local_now.date())
        event_time = st.time_input("Target Execution Time:", value=datetime.time(14, 30))
        event_type = st.selectbox("Access Medium Format:", ["Virtual", "Walk-in"])

    receivers_input = st.text_area(
        "Intended Recipient Email List (separate by commas or new lines):",
        height=100,
        placeholder="candidate1@gmail.com, candidate2@gmail.com"
    )

    about_event = st.text_area(
        "About Event (Agenda & Description shown on Event Page):",
        height=110,
        placeholder="Describe session highlights, speakers, and agenda..."
    )

    with st.expander("🖼️ Cover Image & Custom Event Page URL (Optional)"):
        cover_mode = st.radio(
            "Event Cover Image Source:",
            options=["None", "Upload Image File", "Paste Image URL"],
            horizontal=True
        )
        cover_url = ""
        if cover_mode == "Upload Image File":
            cover_file = st.file_uploader("Upload Banner Image (PNG/JPG):", type=["png", "jpg", "jpeg", "webp"])
            if cover_file is not None:
                b64_str = base64.b64encode(cover_file.read()).decode("utf-8")
                cover_url = f"data:{cover_file.type};base64,{b64_str}"
                st.image(cover_file, caption="Cover Image Preview", width=260)
        elif cover_mode == "Paste Image URL":
            cover_url = st.text_input("Event Cover Image URL:", placeholder="https://example.com")

        default_portal_url = st.secrets.get("portal_base_url", "")
        portal_base_url = st.text_input(
            "Event Page Web App URL (Auto-loaded from Secrets if configured):",
            value=default_portal_url,
            placeholder="https://google.com"
        )

    st.divider()
    st.subheader("📋 Automatic Registration Form Setup")
    reg_choice = st.radio(
        "Choose what guests fill out before accepting the invite:",
        options=[
            "Option 1: Standard Registration (Name & Email only)",
            "Option 2: Custom Registration Form (Add custom questions automatically)"
        ],
        index=0
    )

    custom_questions = ""
    if "Option 2" in reg_choice:
        custom_questions = st.text_input(
            "Enter Custom Questions (comma-separated — Name & Email are already included):",
            placeholder="e.g., Company Name, Job Title, Phone Number, Years of Experience"
        )

    uploaded_files = st.file_uploader(
        "Upload additional supporting materials/documents (Optional)",
        accept_multiple_files=True
    )

    if st.button("🚀 Authorise Workspace & Send Invitations", type="primary"):
        if not company or not event_title or not receivers_input:
            st.error("Please fill in Company Name, Event Title, and Recipient Emails.")
            st.stop()

        if "Option 2" in reg_choice and not custom_questions.strip():
            st.error("Please enter at least one custom question for Option 2.")
            st.stop()

        try:
            raw_tokens = receivers_input.replace("\n", ",").split(",")
            clean_recipients = [r.strip() for r in raw_tokens if "@" in r]

            if not clean_recipients:
                st.error("No valid email addresses containing '@' were found.")
                st.stop()

            d_str = event_date.strftime("%Y-%m-%d")
            t_str = event_time.strftime("%H:%M")
            campaign_id = f"{company.strip().lower().replace(' ', '_')}_{d_str}_{t_str.replace(':', '-')}_{event_type.lower()}"
            reg_mode_code = "CUSTOM_FORM" if "Option 2" in reg_choice else "BUILTIN"

            save_campaign_metadata({
                "campaign_id": campaign_id,
                "company": company.strip(),
                "host_name": host_name.strip() or company.strip(),
                "event_title": event_title.strip(),
                "date_str": d_str,
                "time_str": t_str,
                "event_type": event_type,
                "tz_name": active_tz,
                "about_event": about_event.strip(),
                "cover_url": cover_url.strip(),
                "join_link": "",
                "reg_mode": reg_mode_code,
                "custom_questions": custom_questions.strip()
            })

            GSheetsDatabase.get_or_create_worksheet(company, d_str, t_str, event_type)

            ui_progress = st.progress(0)
            ui_status = st.empty()

            for index, recipient in enumerate(clean_recipients):
                ui_status.text(f"Processing registration & dispatching invite for: {recipient}")

                GSheetsDatabase.write_participant_state(
                    company, d_str, t_str, event_type, recipient, "PENDING", tz_name=active_tz
                )

                clean_base = portal_base_url.strip().rstrip("/")
                guest_event_url = f"{clean_base}?{urlencode({'event': campaign_id, 'email': recipient})}" if clean_base else ""

                try:
                    GmailDispatcher.dispatch_invite(
                        recipient, company, d_str, t_str, event_type, uploaded_files,
                        tz_name=active_tz, event_title=event_title,
                        event_page_url=guest_event_url,
                        accept_url=guest_event_url
                    )
                except TypeError:
                    GmailDispatcher.dispatch_invite(
                        recipient, company, d_str, t_str, event_type, uploaded_files, tz_name=active_tz
                    )

                ui_progress.progress((index + 1) / len(clean_recipients))
                if len(clean_recipients) > 1:
                    time.sleep(1.0)

            ui_status.empty()
            st.success(f"Successfully deployed {len(clean_recipients)} invitations in {active_tz}! 🚀")
            if portal_base_url.strip():
                preview_link = f"{portal_base_url.strip().rstrip('/')}?event={campaign_id}"
                st.info(f"🔗 **Preview Guest Event Page:** [{preview_link}]({preview_link})")

        except EventManagerException as error:
            st.error(f"Application flow interruption fault caught: {str(error)}")
elif selected_page == "📊 Cloud Database Roster Tracker":
    st.subheader("📊 Google Sheets Synchronization & Roster Visualiser")
    st.markdown("Select your campaign from the dropdown below and click **Sync & Pull Roster**.")

    all_campaigns = get_metadata_worksheet().get_all_records()

    if all_campaigns:
        campaign_map = {
            f"{c['event_title']} — {c['company']} ({c['date_str']} {c['time_str']} | {c['event_type']})": c
            for c in all_campaigns
        }
        selected_label = st.selectbox("📂 Select Active Campaign:", options=list(campaign_map.keys()))
        chosen_meta = campaign_map[selected_label]

        sc = chosen_meta["company"]
        sd = chosen_meta["date_str"]
        st_t = chosen_meta["time_str"]
        sty = chosen_meta["event_type"]
    else:
        st.info("No saved campaigns found yet. Enter tab parameters manually below:")
        c1, c2, c3, c4 = st.columns(4)
        sc = c1.text_input("Filter Company Name Key:", value="Infosys")
        sd = c2.text_input("Filter Date Matrix (YYYY-MM-DD):", value=current_local_now.strftime("%Y-%m-%d"))
        st_t = c3.text_input("Filter Time String (HH:MM):", value="14:30")
        sty = c4.selectbox("Filter Operational Type Map:", ["Virtual", "Walk-in"])
        chosen_meta = None

    if st.button("🔄 Sync Inbox & Pull Roster Sheet Data", type="primary"):
        with st.spinner("Syncing Gmail RSVPs & loading Roster..."):
            try:
                logs = GmailListener.poll_and_sync_rsvps(default_tz=active_tz)
                if logs:
                    for log_entry in logs:
                        st.toast(log_entry, icon="✅")
                    st.success(f"Inbox synced! Processed {len(logs)} email RSVP response(s).")

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

    st.divider()
    st.subheader("📩 Post-Registration: Send Joining Link & Calendar Invite (.ics)")
    st.markdown("Add the meeting link or venue address below and send the final confirmation email with `.ics` attachment to all **ACCEPTED** guests.")

    existing_join_link = chosen_meta.get("join_link", "") if chosen_meta else ""
    final_join_link = st.text_input(
        "Meeting Join Link or Venue Address:",
        value=existing_join_link,
        placeholder="https://google.com"
    )

    if st.button("📨 Send Confirmation + .ics Calendar Invite to Accepted Guests"):
        if not chosen_meta:
            st.error("Campaign metadata not found.")
        elif not final_join_link.strip():
            st.error("Please enter the Meeting Join Link or Venue Address first.")
        else:
            chosen_meta["join_link"] = final_join_link.strip()
            save_campaign_metadata(chosen_meta)

            worksheet = GSheetsDatabase.get_or_create_worksheet(sc, sd, st_t, sty)
            accepted_guests = [
                r["Email"] for r in worksheet.get_all_records()
                if str(r.get("RSVP_Status", "")).upper() == "ACCEPTED" and "@" in str(r.get("Email", ""))
            ]

            if not accepted_guests:
                st.warning("No ACCEPTED guests found in this roster tab yet.")
            else:
                sent_count = 0
                for guest_email in accepted_guests:
                    if hasattr(GmailDispatcher, "dispatch_confirmation"):
                        GmailDispatcher.dispatch_confirmation(
                            guest_email, chosen_meta["company"], chosen_meta["event_title"],
                            chosen_meta["date_str"], chosen_meta["time_str"], chosen_meta["event_type"],
                            final_join_link.strip(), tz_name=chosen_meta.get("tz_name", active_tz)
                        )
                        sent_count += 1
                if sent_count > 0:
                    st.success(f"Sent 'Registration Confirmed' + .ics calendar invite to {sent_count} accepted guest(s)! 🎉")
                else:
                    st.info("Saved the Meeting Join Link! Update `gmail_dispatcher.py` with `dispatch_confirmation()` to send the `.ics` confirmation emails.")
