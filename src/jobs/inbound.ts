// Inkomende mail verwerken (§8): koppelen aan enrollment, classificeren,
// stop-condities toepassen, lead/referral/replydraft aanmaken.
import { prisma } from '@/lib/db';
import { classifyReply } from '@/ai/classify';
import { stopsEnrollment, isHardBounce, isComplaint, OOO_PAUSE_DAYS } from '@/core/classify';
import { checkDomainComplaints } from '@/core/guardrails';
import { suppress } from '@/core/suppression';
import { extractReferral } from '@/ai/referral';
import { generateReplyDraft } from '@/reply-assistant/engine';
import { notifyTeam } from './notify';
import { logger } from '@/lib/logger';

export interface InboundMail {
  mailboxEmail: string;
  fromEmail: string;
  subject: string;
  body: string;
  messageId: string;
  inReplyTo?: string;
  references?: string[];
  receivedAt: Date;
}

/** Zoekt de enrollment bij een inkomende mail via In-Reply-To/References + afzender. */
export async function matchEnrollment(mail: InboundMail): Promise<{ enrollmentId: string; tenantId: string; contactId: string; campaignId: string } | null> {
  const refs = [mail.inReplyTo, ...(mail.references ?? [])].filter(Boolean) as string[];
  if (refs.length > 0) {
    const outMsg = await prisma.message.findFirst({
      where: { messageId: { in: refs }, direction: 'OUT', enrollmentId: { not: null } },
      include: { enrollment: true },
    });
    if (outMsg?.enrollment) {
      return {
        enrollmentId: outMsg.enrollment.id,
        tenantId: outMsg.tenantId,
        contactId: outMsg.enrollment.contactId,
        campaignId: outMsg.enrollment.campaignId,
      };
    }
  }
  // Fallback: afzenderadres.
  const contact = await prisma.contact.findFirst({
    where: { email: mail.fromEmail.toLowerCase() },
    include: { enrollments: { where: { status: { in: ['ACTIVE', 'PENDING_APPROVAL', 'PENDING_PERSONALIZATION'] } }, take: 1, orderBy: { createdAt: 'desc' } } },
  });
  if (contact && contact.enrollments[0]) {
    return {
      enrollmentId: contact.enrollments[0].id,
      tenantId: contact.tenantId,
      contactId: contact.id,
      campaignId: contact.enrollments[0].campaignId,
    };
  }
  return null;
}

export async function processInbound(mail: InboundMail): Promise<void> {
  const dupe = await prisma.message.findFirst({ where: { messageId: mail.messageId, direction: 'IN' } });
  if (dupe) return;

  const match = await matchEnrollment(mail);
  if (!match) {
    logger.info({ messageId: mail.messageId }, 'inbound_unmatched');
    return;
  }

  const bounceLike = isHardBounce(`${mail.subject}\n${mail.body}`) || /mailer-daemon|postmaster/i.test(mail.fromEmail);
  const complaint = isComplaint(mail.subject, mail.body);
  const classification = bounceLike ? 'BOUNCE' : await classifyReply(mail.subject, mail.body);

  const message = await prisma.message.create({
    data: {
      enrollmentId: match.enrollmentId,
      tenantId: match.tenantId,
      direction: 'IN',
      messageId: mail.messageId,
      inReplyTo: mail.inReplyTo,
      subject: mail.subject,
      body: mail.body,
      classifiedAs: classification,
      fromEmail: mail.fromEmail.toLowerCase(),
      toEmail: mail.mailboxEmail,
      mailboxEmail: mail.mailboxEmail,
      receivedAt: mail.receivedAt,
    },
  });

  const enrollment = await prisma.enrollment.findUnique({
    where: { id: match.enrollmentId },
    include: { contact: true, mailbox: { include: { sendingDomain: true } }, campaign: true },
  });
  if (!enrollment) return;

  // Spamklacht (§7d): enrollment stoppen, globale suppressie, domeinteller.
  if (complaint) {
    await suppress(null, enrollment.contact.email, 'COMPLAINT');
    const domain = await prisma.sendingDomain.update({
      where: { id: enrollment.mailbox.sendingDomainId },
      data: { complaintCount: { increment: 1 } },
    });
    const dec = checkDomainComplaints(domain.complaintCount);
    if (dec.pause) {
      await prisma.sendingDomain.update({ where: { id: domain.id }, data: { status: 'PAUSED' } });
      await notifyTeam('guardrail', 'Domein gepauzeerd', `Domein ${domain.domain}: ${dec.reason}`, match.tenantId);
    }
    return;
  }

  if (classification === 'BOUNCE') {
    const hard = isHardBounce(`${mail.subject}\n${mail.body}`);
    await prisma.mailbox.update({ where: { id: enrollment.mailboxId }, data: { bouncedToday: { increment: 1 } } });
    await prisma.activity.create({
      data: {
        tenantId: match.tenantId, contactId: match.contactId, campaignId: match.campaignId,
        enrollmentId: match.enrollmentId, type: 'EMAIL_BOUNCED', meta: { hard },
      },
    });
    if (hard) {
      await suppress(null, enrollment.contact.email, 'HARD_BOUNCE');
    } else {
      await prisma.enrollment.update({ where: { id: match.enrollmentId }, data: { status: 'BOUNCED', nextSendAt: null } });
    }
    return;
  }

  if (classification === 'UNSUBSCRIBE') {
    await suppress(match.tenantId, enrollment.contact.email, 'UNSUBSCRIBE');
    return;
  }

  // Reply-activity loggen.
  await prisma.activity.create({
    data: {
      tenantId: match.tenantId, contactId: match.contactId, campaignId: match.campaignId,
      enrollmentId: match.enrollmentId, type: 'EMAIL_REPLIED', meta: { classification, messageId: message.id },
    },
  });

  // Stop-condities (§5): elke reply stopt, behalve OOO (7 dagen pauze).
  if (classification === 'OOO') {
    await prisma.enrollment.update({
      where: { id: match.enrollmentId },
      data: { oooPausedUntil: new Date(Date.now() + OOO_PAUSE_DAYS * 86400_000) },
    });
  } else if (stopsEnrollment(classification)) {
    await prisma.enrollment.update({
      where: { id: match.enrollmentId },
      data: { status: 'REPLIED', nextSendAt: null },
    });
  }

  // POSITIVE → automatisch lead (§8).
  if (classification === 'POSITIVE') {
    const lead = await prisma.lead.create({
      data: {
        tenantId: match.tenantId,
        contactId: match.contactId,
        campaignId: match.campaignId,
        replySnippet: mail.body.slice(0, 300),
        viaReferral: enrollment.contact.source === 'REFERRAL',
      },
    });
    await prisma.activity.create({
      data: {
        tenantId: match.tenantId, contactId: match.contactId, campaignId: match.campaignId,
        enrollmentId: match.enrollmentId, type: 'LEAD_CREATED', meta: { leadId: lead.id },
      },
    });
    await notifyTeam('lead', 'Nieuwe lead', `Positieve reactie van een prospect — bekijk de reply-inbox.`, match.tenantId);
  }

  // REFERRAL → extractie-job (§9).
  if (classification === 'REFERRAL') {
    const extraction = await extractReferral(mail.body, mail.fromEmail);
    await prisma.referral.create({
      data: {
        tenantId: match.tenantId,
        sourceContactId: match.contactId,
        sourceMessageId: message.id,
        suggestedName: extraction.suggestedName,
        suggestedEmail: extraction.suggestedEmail,
        suggestedTitle: extraction.suggestedTitle,
        suggestedCompany: extraction.suggestedCompany,
        rawSnippet: extraction.rawSnippet,
      },
    });
    await prisma.activity.create({
      data: {
        tenantId: match.tenantId, contactId: match.contactId, campaignId: match.campaignId,
        enrollmentId: match.enrollmentId, type: 'REFERRAL_RECEIVED', meta: { messageId: message.id },
      },
    });
    await notifyTeam('referral', 'Nieuwe referral-suggestie', 'Een reply bevat een doorverwijzing — bekijk de referral-werklijst.', match.tenantId);
  }

  // ReplyDraft klaarzetten (§10) — voor alle replies behalve bounce/unsub/ooo.
  await generateReplyDraft(message.id);
}
