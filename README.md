# Direct-Email Automated Event Manager

An infrastructure engine enabling event spreadsheet creation, tracking, and management completely driven over background email loops without frontend dashboards.

## 🛠️ Environment Configuration Setup
Create a `.env` file in the root workspace folder:

```env
PORT=3000
HOST_EMAIL=your_personal_email@gmail.com
INBOUND_DOMAIN=yourdomain.com
SMTP_HOST=://resend.com
SMTP_PORT=465
SMTP_USER=resend
SMTP_PASS=re_your_secret_api_key
```

## 🚀 Execution Guide
1. Run `npm install` to download dependencies.
2. Launch core infrastructure loop using `npm start`.
3. Configure your domain registrar webhook routing inbound emails to `https://<your-server-ip>/api/v1/inbound-email`.
