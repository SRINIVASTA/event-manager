# ✉️ Uttaram — Enterprise Event Communications Engine (Localhost Edition)

An automated event invitation, calendar dispatch, and live RSVP tracking web server running locally on **`http://localhost:8000`** using **FastAPI**, **Gmail SMTP/IMAP**, and **Google Sheets APIs**.

Uttaram sends responsive HTML event invitations with timezone-aware `.ics` calendar attachments, logs initial guest states in Google Sheets, and automatically synchronizes inbound email RSVP confirmations (`ACCEPTED` / `DECLINED`) in the background every 60 seconds.

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    subgraph UI["🖥️ Localhost Web Portal (http://localhost:8000)"]
        TZ["🌍 Regional Timezone Selector\n(IST, EST, PST, GMT, etc.)"]
        T1["🆕 Launch Campaign Portal (/send)"]
        T2["📊 Cloud Database Roster Tracker (/roster)"]
        BG["⏱️ Async Background Worker\n(Auto-Syncs Gmail Every 60s)"]
    end

    subgraph CORE["⚙️ Core Configuration & Local Secrets"]
        CFG["SystemConfig (config.py)"]
        ENV[".env & service_account.json\n(Gmail App Password & GCP JSON Key)"]
    end

    subgraph SERVICES["🔌 Integration Services"]
        DISP["GmailDispatcher\n(SMTP + HTML + .ics)"]
        LIST["GmailListener\n(IMAP Subject Parser)"]
        DB["GSheetsDatabase\n(gspread Service Account)"]
    end

    subgraph EXTERNAL["☁️ External Cloud & Email Infrastructure"]
        SMTP["Gmail SMTP Server\n(://gmail.com)"]
        IMAP["Gmail IMAP Inbox\n(://gmail.com)"]
        GUEST["👤 Invited Guest Inbox"]
        GSHEET["📗 Master Google Spreadsheet\n(Dynamic Event Tabs)"]
    end

    ENV --> CFG
    TZ --> T1 & T2
    CFG --> DISP & LIST & DB

    T1 -->|"1. Create Tab & Log PENDING"| DB
    T1 -->|"2. Dispatch Invites"| DISP
    DB --> GSHEET
    DISP --> SMTP --> GUEST

    GUEST -->|"3. Click Accept / Decline (mailto:)"| IMAP
    BG -->|"4a. Auto-Poll Every 60s"| LIST
    T2 -->|"4b. Manual Sync & Pull Roster"| LIST
    LIST --> IMAP
    LIST -->|"5. Update ACCEPTED / DECLINED"| DB
    DB -->|"6. Render Live Metrics & Table"| T2
```

---

## 🔄 End-to-End RSVP Lifecycle

```mermaid
sequenceDiagram
    actor Organizer as Event Organizer (Localhost)
    participant Server as Uttaram FastAPI Server (:8000)
    participant Sheets as Google Sheets API
    participant Gmail as Gmail (SMTP / IMAP)
    actor Guest as Invited Attendee

    Organizer->>Server: Submit Campaign Form at http://localhost:8000
    Server->>Sheets: Create Event Tab (e.g., infosys_2026-11-11_14-30_virtual)
    loop For Each Recipient
        Server->>Sheets: Append Row (Email, PENDING, Local Timestamp)
        Server->>Gmail: Send Uttaram HTML Card + .ics Invite via SMTP
        Gmail-->>Guest: Deliver Invitation Email
    end

    Guest->>Gmail: Click "✓ Accept Invite" or "✕ Decline" (Sends RSVP Subject)
    Note over Server,Gmail: Background worker polls IMAP every 60s automatically
    Server->>Gmail: Fetch Inbound Emails with "RSVP " Subject
    Gmail-->>Server: Return Matching Guest Replies
    Server->>Sheets: Update Row Status (PENDING ➔ ACCEPTED / DECLINED)
    Organizer->>Server: Click "🔄 Sync Inbox & Pull Roster Sheet Data"
    Sheets-->>Organizer: Display Updated Attendance Metrics & Table
```

---

## ✨ Key Features

* **Standalone Localhost Web Server**: Runs directly on `http://localhost:8000` via FastAPI and Uvicorn with zero third-party cloud hosting dependencies.
* **Hands-Free 60-Second Background Sync**: Includes an asynchronous background worker that continuously polls your Gmail inbox every 60 seconds and updates Google Sheets automatically.
* **Uttaram Branded HTML Invitations**: Responsive, table-based email cards with gradient banners, structured event metadata, and one-click `mailto:` RSVP action buttons.
* **Timezone-Aware `.ics` Calendar Invites**: Uses Python's `zoneinfo` module to generate accurate local timestamps for **India (`Asia/Kolkata`)**, **USA (`America/New_York`, `America/Los_Angeles`, etc.)**, **UK**, **UAE**, **Singapore**, and **Australia**.
* **Automated Google Sheets Provisioning**: Dynamically creates and manages individual worksheet tabs per campaign (`{company}_{date}_{time}_{type}`) without overwriting past events.
* **Multi-File Attachments**: Supports attaching PDFs, agendas, or onboarding guides alongside the `.ics` calendar file.

---

## 📂 Project Structure

```text
uttaram-localhost/
├── main.py                             # FastAPI server & background RSVP sync worker
├── .env                                # Local environment variables (Gmail & Sheet ID)
├── service_account.json                # Google Cloud Service Account credentials JSON
├── requirements.txt                    # Python dependencies
├── README.md                           # Project documentation
└── src/
    ├── core/
    │   ├── config.py                   # Loads .env & service_account.json
    │   └── exceptions.py               # Custom domain exceptions
    ├── services/
    │   ├── gmail_dispatcher.py         # SMTP email & .ics calendar generator
    │   ├── gmail_listener.py           # IMAP reply parser & RSVP synchronizer
    │   └── gsheets_database.py         # Google Sheets API wrapper (gspread)
    └── templates/
        ├── index.html                  # Localhost web portal interface
        └── invite_template.html        # Responsive Uttaram HTML email template
```

---

## 🚀 Localhost Setup & Installation

### 1. Clone & Install Dependencies
```bash
git clone <your-repository-url>
cd uttaram-localhost
pip install -r requirements.txt
```

```

### 2. Start the Localhost Server
```bash
uvicorn main:app --reload --port 8000
```
Open your browser and navigate to **`http://localhost:8000`**.

---

## 🛠️ Usage Guide

1. **Select Region / Timezone**: Choose your active region at the top of `http://localhost:8000` (defaults to **India `IST - Asia/Kolkata`**).
2. **Launch Campaign**: Under **🆕 Launch Campaign Portal**, enter the company/program name, date, time, format (`Virtual` or `Walk-in`), and recipient email addresses, then click **🚀 Authorise Workspace & Send Invitations**.
3. **Track Live Attendance**: Replies are synced automatically in the background every 60 seconds, or you can click **🔄 Sync Inbox & Pull Roster Sheet Data** under **📊 Cloud Database Roster Tracker** to refresh the table immediately.
