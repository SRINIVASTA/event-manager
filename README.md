# ✉️ Uttaram — Enterprise Event Communications & RSVP Engine

**Uttaram** is an automated, cloud-ready event invitation, dynamic guest registration, and live RSVP tracking application built with **Streamlit**, **Gmail SMTP/IMAP**, and the **Google Sheets API**.

---

## ✨ Key Features

- **Dual-Mode Streamlit Portal**:
  - **Admin Workspace**: Private organizer dashboard with two navigation views (**Launch Campaign Portal** and **Cloud Database Roster Tracker**) plus multi-timezone support (`IST`, `EST`, `PST`, `GMT`, `GST`, `SGT`, `AEST`, `UTC`).
  - **Guest Event Landing Page (`?event=<campaign_id>`)**: Automatically hides the admin sidebar to render a clean, branded event page with cover banner, organizer info, live **Going** counter, formatted agenda, and instant registration.
- **Two Flexible Registration Modes**:
  - **Option 1 (Standard Registration)**: Collects `Full Name` and `Email` directly on the Event Page.
  - **Option 2 (Custom Registration Form)**: Automatically generates custom input fields (e.g., `Company Name`, `Job Title`, `Phone Number`) and dynamically appends matching columns to your Google Sheet roster tab.
- **Two-Stage Email & Calendar Workflow**:
  1. **Initial Invitation (`invite_template.html`)**: Sends a branded HTML email with **✓ Accept Invite**, **View Event**, and **✕ Decline** actions while keeping private meeting links hidden.
  2. **Post-Registration Confirmation (`.ics`)**: After registration, dispatches a **"Registration confirmed"** email containing the private **Meeting Join Link / Venue Address** and a timezone-aware **`.ics` calendar attachment**.
- **Automated Google Sheets Database (`gspread`)**:
  - Stores event configurations in `Campaigns_Metadata_00-00_config`.
  - Provisions isolated per-event roster tabs (`{company}_{date}_{time}_{type}`) with case-insensitive lookup and real-time RSVP status tracking (`PENDING`, `ACCEPTED`, `DECLINED`).

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    subgraph Admin["🧑‍💼 Organizer Admin Portal (Streamlit)"]
        A1["🆕 Launch Campaign Portal"]
        A2["📊 Cloud Database Roster Tracker"]
    end

    subgraph Guest["🎟️ Public Guest Experience"]
        G1["📧 Branded HTML Invite Email"]
        G2["🌐 Event Landing Page (?event=ID)"]
        G3["✅ 'You're In' Confirmation Card"]
    end

    subgraph Cloud["☁️ Backend & Cloud Services"]
        S1["📊 Google Sheets API (Metadata & Event Rosters)"]
        S2["📤 Gmail SMTP (Invites & .ics Confirmations)"]
        S3["📥 Gmail IMAP (Email Decline/RSVP Listener)"]
    end

    %% Running Data & Communication Flows
    A1 e1@-->|"1. Save Event Config & Create Tab"| S1
    A1 e2@-->|"2. Dispatch Initial Invites"| S2
    S2 e3@--> G1
    G1 e4@-->|"3. Click Accept / View Event"| G2
    G2 e5@-->|"4. Submit Standard or Custom Form"| S1
    G2 e6@--> G3
    A2 e7@-->|"5. Poll Inbox & Pull Live Roster"| S3
    S3 e8@--> S1
    A2 e9@-->|"6. Send Joining Link + .ics Calendar"| S2

    %% Running Flow Animation Definitions
    e1@{ animate: true }
    e2@{ animate: true }
    e3@{ animate: true }
    e4@{ animate: true }
    e5@{ animate: true }
    e6@{ animate: true }
    e7@{ animate: true }
    e8@{ animate: true }
    e9@{ animate: true }
```

---

## 🔄 End-to-End RSVP & Confirmation Lifecycle

```mermaid
sequenceDiagram
    autonumber
    actor Organizer
    participant App as Streamlit App (app.py)
    participant Sheets as Google Sheets
    participant Gmail as Gmail SMTP / IMAP
    actor Guest

    rect rgb(227, 242, 253)
    Note right of Organizer: Stage 1: Campaign Creation & Initial Invitation
    Organizer->>App: Configure Event & Choose Registration Mode (Option 1 or 2)
    App->>Sheets: Save Metadata & Create Event Roster Tab (PENDING)
    App->>Gmail: Send Initial Branded Invite (Accept / View / Decline)
    Gmail-->>Guest: Delivers Invitation Email
    end

    rect rgb(232, 245, 233)
    Note right of Organizer: Stage 2: Guest Landing & RSVP Registration
    Guest->>App: Clicks "View Event" or "Accept Invite" (?event=ID)
    App->>Sheets: Fetch Event Metadata & Live "Going" Count
    App-->>Guest: Render Branded Event Page & Registration Form
    Guest->>App: Submits Name, Email & Custom Answers
    App->>Sheets: Update Status to ACCEPTED & Save Custom Columns
    App-->>Guest: Display "✓ You’re In" Confirmation Screen
    end

    rect rgb(255, 243, 224)
    Note right of Organizer: Stage 3: Access Link & Calendar Dispatch
    Organizer->>App: Enter Meeting Link / Venue in Roster Tracker
    App->>Gmail: Dispatch "Registration Confirmed" + .ics Attachment
    Gmail-->>Guest: Delivers Calendar Invite & Access Link
    end
```

---

## 📂 Project Structure

```text
event-manager/
├── app.py                              # Unified Streamlit Admin & Guest Event Portal
├── requirements.txt                    # Python dependencies (streamlit, gspread, ics, pandas)
├── README.md                           # Project documentation & architecture diagrams
└── src/
    ├── core/
    │   ├── config.py                   # Streamlit Secrets configuration loader
    │   └── exceptions.py               # Custom application exception classes
    ├── services/
    │   ├── gsheets_database.py         # Google Sheets tab & participant state manager
    │   ├── gmail_dispatcher.py         # SMTP HTML email & .ics calendar generator
    │   └── gmail_listener.py           # IMAP inbox RSVP parser
    └── templates/
        └── invite_template.html        # Responsive HTML invitation email template
```

---

## 🚀 Quick Start & Configuration

### 1. Install Dependencies
```bash
git clone https://github.com
cd event-manager
pip install -r requirements.txt
```

### 2. Run Locally
```bash
streamlit run app.py
```

---

## 📋 Usage Guide

1. **Launch a Campaign**:
   - Open **🆕 Launch Campaign Portal**, select your active timezone, and fill in the **Organization Name**, **Host Name**, **Event Title**, **Date/Time**, and **About Event** agenda.
   - Choose **Option 1** (Name & Email only) or **Option 2** (add custom comma-separated questions).
   - Enter recipient email addresses and click **🚀 Authorise Workspace & Send Invitations**.
2. **Track RSVPs & Send Joining Links**:
   - Open **📊 Cloud Database Roster Tracker**, select your campaign from the dropdown, and click **🔄 Sync Inbox & Pull Roster Sheet Data**.
   - Enter the **Meeting Join Link or Venue Address** and click **📨 Send Confirmation + .ics Calendar Invite to Accepted Guests**.
