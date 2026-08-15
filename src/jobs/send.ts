// Verzendjob: de enige plek waar een campagnemail daadwerkelijk verstuurd wordt.
// Bevat de harde verzendpoort (canSend) — bescherming zit hier, niet in de UI.
import { prisma } from '@/lib/db';
import { canSend, checkCampaignBounceRate, checkMailboxHealth } from '@/core/guardrails';
import { CAMPAIGN_BOUNCE_WINDOW } from '@/core/guardrails';
import { isSuppressed } from '@/core/suppression';
import { renderTemplate, buildVars } from '@/core/template';
import { sendMail } from '@/mail/send';
import { notifyTeam } from './notify';
import { logger } from '@/lib/logger';
import { randomUUID } from 'crypto';

export async function processSend(enrollmentId: string): Promise<void> {
  const e = await prisma.enrollment.findUnique({
    where: { id: enrollmentId },
    include: {
      campaign: { include: { sequenceSteps: { orderBy: { order: 'asc' } }, tenant: true } },
      contact: { include: { company: true } },
      mailbox: { include: { sendingDomain: true } },
    },
  });
  if (!e) return;
  const step = e.campaign.sequenceSteps[e.currentStep];
  if (!step) {
    await prisma.enrollment.update({ where: { id: e.id }, data: { status: 'COMPLETED', nextSendAt: null } });
    return;
  }

  // OOO-pauze afgelopen? Zo niet: overslaan.
  if (e.oooPausedUntil && e.oooPausedUntil > new Date()) return;

  const suppressed = await isSuppressed(e.contact.tenantId, e.contact.email);
  const gate = canSend({
    domainStatus: e.mailbox.sendingDomain.status,
    domainSpfOk: e.mailbox.sendingDomain.spfOk,
    domainDkimOk: e.mailbox.sendingDomain.dkimOk,
    mailboxStatus: e.mailbox.status,
    mailboxSentToday: e.mailbox.sentToday,
    mailboxDailyCap: e.mailbox.dailyCap,
    campaignStatus: e.campaign.status,
    enrollmentStatus: e.status,
    suppressed,
    emailStatus: e.contact.emailStatus,
    hasUnsubscribeLink: true, // footer + List-Unsubscribe worden altijd door de verzendengine geïnjecteerd
  });
  if (!gate.allowed) {
    logger.info({ enrollmentId, reason: gate.reason }, 'send_blocked');
    // Niet fataal: enrollment blijft staan; scheduler probeert later opnieuw
    // (tenzij de status zelf het blokkeert — dan gebeurt er vanzelf niets meer).
    await prisma.enrollment.update({ where: { id: e.id }, data: { nextSendAt: null } });
    return;
  }

  // Template renderen; ontbrekende variabelen blokkeren verzending (§5).
  const useB = e.variant === 'B' && step.subjectB && step.bodyB;
  const subjectTpl = useB ? step.subjectB! : step.subjectA;
  const bodyTpl = useB ? step.bodyB! : step.bodyA;
  const vars = buildVars({
    firstName: e.contact.firstName,
    lastName: e.contact.lastName,
    companyName: e.contact.company.name,
    title: e.contact.title,
    city: e.contact.company.city,
    opener: e.personalizedOpener,
    customFields: (e.contact.customFields as Record<string, unknown>) ?? {},
  });
  const subject = renderTemplate(subjectTpl, vars);
  const body = renderTemplate(bodyTpl, vars);
  if (!subject.ok || !body.ok) {
    logger.warn({ enrollmentId, missing: [...subject.missing, ...body.missing] }, 'send_blocked_missing_vars');
    await prisma.activity.create({
      data: {
        tenantId: e.contact.tenantId,
        contactId: e.contactId,
        campaignId: e.campaignId,
        enrollmentId: e.id,
        type: 'NOTE',
        meta: { warning: 'Verzending geblokkeerd: ontbrekende variabelen', missing: [...subject.missing, ...body.missing] },
      },
    });
    await prisma.enrollment.update({ where: { id: e.id }, data: { nextSendAt: null } });
    return;
  }

  const trackingToken = randomUUID();
  const result = await sendMail(e.mailbox, {
    tenantId: e.contact.tenantId,
    to: e.contact.email,
    subject: subject.text,
    bodyText: body.text,
    senderAddress: e.campaign.tenant.senderAddress || e.campaign.tenant.name,
    trackingEnabled: e.campaign.trackingEnabled,
    trackingToken,
  });

  if (!result.ok) {
    const mb = await prisma.mailbox.update({
      where: { id: e.mailbox.id },
      data: { consecutiveSmtpErrors: { increment: 1 }, lastError: result.error?.slice(0, 500) },
    });
    const health = checkMailboxHealth(mb);
    if (health.pause) {
      await prisma.mailbox.update({ where: { id: mb.id }, data: { status: 'PAUSED' } });
      await notifyTeam('guardrail', `Mailbox gepauzeerd`, `Mailbox ${mb.email}: ${health.reason}`, e.contact.tenantId);
    }
    return;
  }

  // Succes: state bijwerken (in DB, herstart-veilig) en Activity + Message loggen.
  await prisma.$transaction([
    prisma.mailbox.update({
      where: { id: e.mailbox.id },
      data: { sentToday: { increment: 1 }, consecutiveSmtpErrors: 0 },
    }),
    prisma.message.create({
      data: {
        enrollmentId: e.id,
        tenantId: e.contact.tenantId,
        direction: 'OUT',
        messageId: result.messageId,
        subject: subject.text,
        body: result.renderedText,
        fromEmail: e.mailbox.email,
        toEmail: e.contact.email,
        mailboxEmail: e.mailbox.email,
        sentAt: new Date(),
      },
    }),
    prisma.activity.create({
      data: {
        tenantId: e.contact.tenantId,
        contactId: e.contactId,
        campaignId: e.campaignId,
        enrollmentId: e.id,
        type: 'EMAIL_SENT',
        meta: { step: e.currentStep, variant: e.variant, trackingToken, messageId: result.messageId },
      },
    }),
  ]);

  // Volgende stap plannen of afronden.
  const nextStep = e.campaign.sequenceSteps[e.currentStep + 1];
  if (nextStep) {
    const nextSendAt = new Date(Date.now() + nextStep.waitDays * 86400_000);
    await prisma.enrollment.update({
      where: { id: e.id },
      data: { currentStep: { increment: 1 }, nextSendAt },
    });
  } else {
    await prisma.enrollment.update({
      where: { id: e.id },
      data: { status: 'COMPLETED', nextSendAt: null },
    });
  }

  // Guardrail: campagne-bounce-rate over de laatste 100 verzonden mails.
  const recentSent = await prisma.activity.findMany({
    where: { campaignId: e.campaignId, type: { in: ['EMAIL_SENT', 'EMAIL_BOUNCED'] } },
    orderBy: { occurredAt: 'desc' },
    take: CAMPAIGN_BOUNCE_WINDOW,
    select: { type: true },
  });
  const sentCount = recentSent.filter((a) => a.type === 'EMAIL_SENT').length;
  const bounceCount = recentSent.filter((a) => a.type === 'EMAIL_BOUNCED').length;
  const decision = checkCampaignBounceRate(sentCount + bounceCount, bounceCount);
  if (decision.pause) {
    await prisma.campaign.update({ where: { id: e.campaignId }, data: { status: 'PAUSED' } });
    await notifyTeam('guardrail', 'Campagne gepauzeerd', `Campagne "${e.campaign.name}": ${decision.reason}`, e.contact.tenantId);
  }
}
