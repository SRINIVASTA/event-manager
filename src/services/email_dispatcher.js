import nodemailer from 'nodemailer';
import { createEvent } from 'ics';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const transporter = nodemailer.createTransport({
  host: process.env.SMTP_HOST || "://resend.com",
  port: parseInt(process.env.SMTP_PORT || "465"),
  secure: true,
  auth: {
    user: process.env.SMTP_USER,
    pass: process.env.SMTP_PASS,
  },
});

export class EmailDispatcher {
  static async sendInvitation({ to, company, date, time, type }) {
    // 1. Generate unique dynamic system email alias tracking string
    const eventPayload = JSON.stringify({ company, date, time, type });
    const trackingHex = Buffer.from(eventPayload).toString('hex');
    const systemTrackingEmail = `event-${trackingHex}@${process.env.INBOUND_DOMAIN}`;

    // 2. Generate Calendar Event (.ics attachment context)
    const [year, month, day] = date.split('-').map(Number);
    const [hour, minute] = time.split(':').map(Number);

    const { value } = createEvent({
      start: [year, month, day, hour, minute],
      duration: { hours: 1 },
      title: `${company} - Programme Invitation`,
      location: type.toLowerCase() === 'virtual' ? 'Virtual Link' : 'Walk-in Venue Address',
    });

    // 3. Load HTML Template & Replace Variables
    const templatePath = path.join(__dirname, '../templates/invite_template.html');
    let html = fs.readFileSync(templatePath, 'utf8');
    html = html
      .replace(/{{COMPANY_NAME}}/g, company)
      .replace(/{{DATE}}/g, date)
      .replace(/{{TIME}}/g, time)
      .replace(/{{TYPE}}/g, type)
      .replace(/{{REPLY_EMAIL}}/g, systemTrackingEmail);

    // 4. Dispatch Outward Mail Pipeline
    await transporter.sendMail({
      from: `"Programmes Office" <office@${process.env.INBOUND_DOMAIN}>`,
      to: to,
      subject: `Invitation: ${company} Programme (${date})`,
      html: html,
      icalEvent: {
        filename: 'invite.ics',
        method: 'REQUEST',
        content: value,
      },
    });
  }

  static async sendHostAlert(toHost, data) {
    const templatePath = path.join(__dirname, '../templates/host_alert.html');
    let html = fs.readFileSync(templatePath, 'utf8');
    html = html
      .replace(/{{COMPANY}}/g, data.company)
      .replace(/{{DATE}}/g, data.date)
      .replace(/{{PARTICIPANT}}/g, data.participant)
      .replace(/{{STATUS}}/g, data.status);

    await transporter.sendMail({
      from: `"System Engine" <noreply@${process.env.INBOUND_DOMAIN}>`,
      to: toHost,
      subject: `System Log Alert: RSVP Action Processed`,
      html: html
    });
  }
}
