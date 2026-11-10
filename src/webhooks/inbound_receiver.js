import { Router } from 'express';
import { EmailParser } from '../services/email_parser.js';
import { FileManager } from '../services/file_manager.js';
import { EmailDispatcher } from '../services/email_dispatcher.js';

const router = Router();

router.post('/inbound-email', async (req, res) => {
  try {
    const { from, to, subject, text, body } = req.body; 
    // Adapts to standard inbound formats payload variations (SendGrid / Resend)
    const senderEmail = from.value?.[0]?.address || from;
    const recipientEmail = to.value?.[0]?.address || to;

    // SCENARIO A: You (Host) are commanding an event instantiation via email rules
    if (senderEmail.toLowerCase() === process.env.HOST_EMAIL.toLowerCase()) {
      const command = EmailParser.parseHostCommand(subject);
      if (command) {
        // Initialises local dynamic workspace files
        const fullPath = FileManager.createEventFile(command.company, command.date, command.time, command.type);
        
        // If your body payload contains a list of participant emails split by lines, extract and push invites
        if (text) {
          const emails = text.split('\n').map(e => e.trim()).filter(e => e.includes('@'));
          for (const email of emails) {
            FileManager.updateParticipantStatus(fullPath, email, 'PENDING');
            await EmailDispatcher.sendInvitation({ to: email, ...command });
          }
        }
        return res.status(200).json({ status: 'Event created, invitations sent.' });
      }
    }

    // SCENARIO B: A Participant interacts via clicking the "Accept" or "Decline" mailto options
    const eventContext = EmailParser.extractTrackingHash(recipientEmail);
    if (eventContext) {
      const isAccept = subject.toUpperCase().includes('ACCEPT');
      const finalStatus = isAccept ? 'ACCEPTED' : 'DECLINED';

      const { fullPath } = FileManager.getFilePath(eventContext.company, eventContext.date, eventContext.time, eventContext.type);
      const updated = FileManager.updateParticipantStatus(fullPath, senderEmail, finalStatus);

      if (updated) {
        // Notify host immediately that execution logs have changed state
        await EmailDispatcher.sendHostAlert(process.env.HOST_EMAIL, {
          ...eventContext,
          participant: senderEmail,
          status: finalStatus
        });
      }
      return res.status(200).json({ status: 'Participant state captured.' });
    }

    res.status(200).json({ status: 'Ignored unrelated noise emails.' });
  } catch (error) {
    console.error('[Webhook Error]', error);
    res.status(500).json({ error: 'Internal system pipeline fault.' });
  }
});

export default router;
