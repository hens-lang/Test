// IMAP-poll-job (§8): haalt per mailbox nieuwe mail op en geeft die door aan
// de inbound-verwerking. In demo-modus wordt IMAP overgeslagen (gesimuleerde
// replies komen binnen via de demo-API of het seed-script).
import { ImapFlow } from 'imapflow';
import { simpleParser } from 'mailparser';
import { prisma } from '@/lib/db';
import { decryptSecret } from '@/lib/crypto';
import { getSendMode } from '@/lib/env';
import { processInbound } from './inbound';
import { logger } from '@/lib/logger';

export async function pollMailbox(mailboxId: string): Promise<void> {
  if (getSendMode() === 'demo') return;
  const mailbox = await prisma.mailbox.findUnique({ where: { id: mailboxId } });
  if (!mailbox || mailbox.status === 'ERROR') return;

  const client = new ImapFlow({
    host: mailbox.imapHost,
    port: mailbox.imapPort,
    secure: mailbox.imapPort === 993,
    auth: { user: mailbox.imapUser, pass: decryptSecret(mailbox.imapPassEncrypted) },
    logger: false,
  });

  try {
    await client.connect();
    const lock = await client.getMailboxLock('INBOX');
    try {
      const startUid = mailbox.lastImapUid + 1;
      let maxUid = mailbox.lastImapUid;
      for await (const msg of client.fetch(`${startUid}:*`, { uid: true, source: true }, { uid: true })) {
        if (msg.uid <= mailbox.lastImapUid) continue;
        maxUid = Math.max(maxUid, msg.uid);
        if (!msg.source) continue;
        const parsed = await simpleParser(msg.source);
        await processInbound({
          mailboxEmail: mailbox.email,
          fromEmail: parsed.from?.value[0]?.address ?? '',
          subject: parsed.subject ?? '',
          body: parsed.text ?? '',
          messageId: parsed.messageId ?? `<imap-${msg.uid}@${mailbox.email.split('@')[1]}>`,
          inReplyTo: parsed.inReplyTo ?? undefined,
          references: Array.isArray(parsed.references) ? parsed.references : parsed.references ? [parsed.references] : undefined,
          receivedAt: parsed.date ?? new Date(),
        });
      }
      if (maxUid > mailbox.lastImapUid) {
        await prisma.mailbox.update({ where: { id: mailboxId }, data: { lastImapUid: maxUid } });
      }
    } finally {
      lock.release();
    }
    await client.logout();
  } catch (err) {
    logger.error({ mailboxId, err: String(err) }, 'imap_poll_failed');
    await prisma.mailbox.update({ where: { id: mailboxId }, data: { lastError: String(err).slice(0, 500) } });
  }
}
