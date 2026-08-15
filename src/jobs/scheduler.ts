// Scheduler-job (§7c): plant per run de verzendbare enrollments in.
// State (sentToday, caps) leeft in de database — nooit in memory — zodat een
// herstart van de app nooit tot capoverschrijding leidt.
import { prisma } from '@/lib/db';
import { planSends, isWithinSendWindow, parseTimeToMinutes, localTimeParts, type MailboxState, type CampaignState } from '@/core/planner';
import { logger } from '@/lib/logger';

export interface ScheduledSend {
  enrollmentId: string;
  sendAt: Date;
}

/**
 * Bepaalt welke enrollments nú ingepland kunnen worden en geeft de planning terug.
 * De worker zet hier pg-boss-jobs voor klaar (sendAfter = sendAt).
 */
export async function planDueSends(now: Date = new Date()): Promise<ScheduledSend[]> {
  const due = await prisma.enrollment.findMany({
    where: {
      status: 'ACTIVE',
      OR: [{ nextSendAt: null }, { nextSendAt: { lte: now } }],
      oooPausedUntil: null,
    },
    include: {
      campaign: true,
      mailbox: true,
      contact: true,
    },
    take: 500,
  });

  const mailboxes = new Map<string, MailboxState>();
  const campaigns = new Map<string, CampaignState>();
  const eligible: { enrollmentId: string; mailboxId: string; campaignId: string }[] = [];
  let windowSecondsLeft = 0;

  for (const e of due) {
    const camp = e.campaign;
    if (!isWithinSendWindow(now, camp, camp.timezone)) continue;
    // Al eerder geplande maar nog niet verzonden mails niet dubbel plannen:
    // markering gebeurt door nextSendAt vooruit te zetten bij het queuen.
    if (!mailboxes.has(e.mailboxId)) {
      mailboxes.set(e.mailboxId, {
        id: e.mailbox.id,
        dailyCap: e.mailbox.dailyCap,
        sentToday: e.mailbox.sentToday,
        status: e.mailbox.status,
      });
    }
    if (!campaigns.has(camp.id)) {
      const sentTodayForCampaign = await prisma.activity.count({
        where: {
          campaignId: camp.id,
          type: 'EMAIL_SENT',
          occurredAt: { gte: startOfDay(now) },
        },
      });
      campaigns.set(camp.id, {
        id: camp.id,
        status: camp.status,
        sendWindowStart: camp.sendWindowStart,
        sendWindowEnd: camp.sendWindowEnd,
        sendDays: camp.sendDays,
        dailyCampaignCap: camp.dailyCampaignCap,
        sentTodayForCampaign,
      });
      const { minutes } = localTimeParts(now, camp.timezone);
      const left = (parseTimeToMinutes(camp.sendWindowEnd) - minutes) * 60;
      windowSecondsLeft = Math.max(windowSecondsLeft, left);
    }
    eligible.push({ enrollmentId: e.id, mailboxId: e.mailboxId, campaignId: camp.id });
  }

  const planned = planSends(eligible, mailboxes, campaigns, now, Math.max(windowSecondsLeft, 0));

  // nextSendAt vooruitzetten zodat een volgende scheduler-run ze niet opnieuw pakt.
  for (const p of planned) {
    await prisma.enrollment.update({
      where: { id: p.enrollmentId },
      data: { nextSendAt: p.sendAt },
    });
  }
  if (planned.length > 0) logger.info({ count: planned.length }, 'sends_planned');
  return planned.map((p) => ({ enrollmentId: p.enrollmentId, sendAt: p.sendAt }));
}

export function startOfDay(d: Date): Date {
  const s = new Date(d);
  s.setUTCHours(0, 0, 0, 0);
  return s;
}
