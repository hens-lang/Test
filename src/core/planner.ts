// Verzendplanner (§7c): plant per mailbox de mails van vandaag binnen het
// verzendvenster, gespreid met random jitter (90–240s), nooit boven dailyCap
// per mailbox of dailyCampaignCap per campagne. Puur en unit-testbaar;
// de scheduler-job voert het resultaat uit via pg-boss.

export const MIN_GAP_SECONDS = 90;
export const MAX_GAP_SECONDS = 240;

export interface PlannableEnrollment {
  enrollmentId: string;
  mailboxId: string;
  campaignId: string;
}

export interface MailboxState {
  id: string;
  dailyCap: number;
  sentToday: number;
  status: 'WARMING' | 'ACTIVE' | 'PAUSED' | 'ERROR';
}

export interface CampaignState {
  id: string;
  status: 'DRAFT' | 'REVIEW' | 'ACTIVE' | 'PAUSED' | 'COMPLETED';
  sendWindowStart: string; // "08:30"
  sendWindowEnd: string; // "17:00"
  sendDays: string; // "1,2,3,4,5" (ISO: 1=ma)
  dailyCampaignCap: number | null;
  sentTodayForCampaign: number;
}

export interface PlannedSend {
  enrollmentId: string;
  mailboxId: string;
  campaignId: string;
  sendAt: Date;
}

export function parseTimeToMinutes(t: string): number {
  const [h, m] = t.split(':').map(Number);
  return h * 60 + (m || 0);
}

/** Weekdag (ISO 1-7) en minuten sinds middernacht in de opgegeven tijdzone. */
export function localTimeParts(now: Date, timezone: string): { isoWeekday: number; minutes: number } {
  const fmt = new Intl.DateTimeFormat('nl-NL', {
    timeZone: timezone,
    weekday: 'short',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  });
  const parts = fmt.formatToParts(now);
  const wd = parts.find((p) => p.type === 'weekday')?.value ?? 'ma';
  const hour = Number(parts.find((p) => p.type === 'hour')?.value ?? '0');
  const minute = Number(parts.find((p) => p.type === 'minute')?.value ?? '0');
  const map: Record<string, number> = { ma: 1, di: 2, wo: 3, do: 4, vr: 5, za: 6, zo: 7 };
  return { isoWeekday: map[wd] ?? 1, minutes: hour * 60 + minute };
}

export function isWithinSendWindow(now: Date, campaign: Pick<CampaignState, 'sendWindowStart' | 'sendWindowEnd' | 'sendDays'>, timezone: string): boolean {
  const { isoWeekday, minutes } = localTimeParts(now, timezone);
  const days = campaign.sendDays.split(',').map((d) => Number(d.trim())).filter(Boolean);
  if (!days.includes(isoWeekday)) return false;
  return minutes >= parseTimeToMinutes(campaign.sendWindowStart) && minutes < parseTimeToMinutes(campaign.sendWindowEnd);
}

/**
 * Plant verzendingen. Willekeur is injecteerbaar (rand) zodat tests deterministisch zijn.
 * Alleen enrollments waarvan mailbox én campagne actief zijn en caps het toelaten
 * krijgen een tijdstip; de rest schuift naar een volgende run.
 */
export function planSends(
  enrollments: PlannableEnrollment[],
  mailboxes: Map<string, MailboxState>,
  campaigns: Map<string, CampaignState>,
  now: Date,
  windowEndsInSeconds: number,
  rand: () => number = Math.random,
): PlannedSend[] {
  const planned: PlannedSend[] = [];
  const mailboxBudget = new Map<string, number>();
  const mailboxNextSlot = new Map<string, number>(); // seconden vanaf now
  const campaignBudget = new Map<string, number>();

  for (const e of enrollments) {
    const mb = mailboxes.get(e.mailboxId);
    const camp = campaigns.get(e.campaignId);
    if (!mb || !camp) continue;
    if (mb.status !== 'ACTIVE' && mb.status !== 'WARMING') continue;
    if (camp.status !== 'ACTIVE') continue;

    if (!mailboxBudget.has(mb.id)) mailboxBudget.set(mb.id, Math.max(0, mb.dailyCap - mb.sentToday));
    if (!campaignBudget.has(camp.id)) {
      campaignBudget.set(
        camp.id,
        camp.dailyCampaignCap === null ? Number.POSITIVE_INFINITY : Math.max(0, camp.dailyCampaignCap - camp.sentTodayForCampaign),
      );
    }

    if ((mailboxBudget.get(mb.id) ?? 0) <= 0) continue;
    if ((campaignBudget.get(camp.id) ?? 0) <= 0) continue;

    const prev = mailboxNextSlot.get(mb.id);
    const gap = MIN_GAP_SECONDS + Math.floor(rand() * (MAX_GAP_SECONDS - MIN_GAP_SECONDS + 1));
    const slot = prev === undefined ? Math.floor(rand() * MIN_GAP_SECONDS) : prev + gap;
    if (slot >= windowEndsInSeconds) continue; // past niet meer in het venster van vandaag

    mailboxNextSlot.set(mb.id, slot);
    mailboxBudget.set(mb.id, (mailboxBudget.get(mb.id) ?? 0) - 1);
    campaignBudget.set(camp.id, (campaignBudget.get(camp.id) ?? 1) - 1);
    planned.push({
      enrollmentId: e.enrollmentId,
      mailboxId: mb.id,
      campaignId: camp.id,
      sendAt: new Date(now.getTime() + slot * 1000),
    });
  }
  return planned;
}

/** Round-robin-toewijzing van mailboxen aan nieuwe enrollments. */
export function assignMailboxesRoundRobin<T>(items: T[], mailboxIds: string[]): { item: T; mailboxId: string }[] {
  if (mailboxIds.length === 0) return [];
  return items.map((item, i) => ({ item, mailboxId: mailboxIds[i % mailboxIds.length] }));
}
