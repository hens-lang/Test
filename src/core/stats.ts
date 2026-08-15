// Gedeelde query-laag (§11/§13/§14): het dashboard, de weekrapportage en het
// maandelijkse waarderapport gebruiken allemaal exact deze functies.
// Eén bron van waarheid — geen dubbele berekeningen.
import { prisma } from '@/lib/db';

export interface FunnelStats {
  approached: number;
  opened: number;
  replied: number;
  leads: number;
  sent: number;
  bounced: number;
  unsubscribed: number;
  replyRate: number; // replies / verzonden
  openRate: number; // onbetrouwbaar (privacy-proxies) — toon met disclaimer
  leadsViaReferral: number;
}

export async function funnelStats(tenantId: string, since?: Date, until?: Date): Promise<FunnelStats> {
  const range = { gte: since, lte: until };
  const where = (type: string) => ({
    tenantId,
    type: type as never,
    ...(since || until ? { occurredAt: range } : {}),
  });

  const [sent, opened, replied, bounced, unsubscribed] = await Promise.all([
    prisma.activity.count({ where: where('EMAIL_SENT') }),
    prisma.activity.count({ where: where('EMAIL_OPENED') }),
    prisma.activity.count({ where: where('EMAIL_REPLIED') }),
    prisma.activity.count({ where: where('EMAIL_BOUNCED') }),
    prisma.activity.count({ where: where('EMAIL_UNSUBSCRIBED') }),
  ]);
  const approached = await prisma.activity
    .groupBy({
      by: ['contactId'],
      where: { tenantId, type: 'EMAIL_SENT', ...(since || until ? { occurredAt: range } : {}) },
    })
    .then((g) => g.length);
  const openedUnique = await prisma.activity
    .groupBy({
      by: ['contactId'],
      where: { tenantId, type: 'EMAIL_OPENED', ...(since || until ? { occurredAt: range } : {}) },
    })
    .then((g) => g.length);
  const repliedUnique = await prisma.activity
    .groupBy({
      by: ['contactId'],
      where: { tenantId, type: 'EMAIL_REPLIED', ...(since || until ? { occurredAt: range } : {}) },
    })
    .then((g) => g.length);
  const leadWhere = { tenantId, ...(since || until ? { createdAt: range } : {}) };
  const [leads, leadsViaReferral] = await Promise.all([
    prisma.lead.count({ where: leadWhere }),
    prisma.lead.count({ where: { ...leadWhere, viaReferral: true } }),
  ]);

  return {
    approached,
    opened: openedUnique,
    replied: repliedUnique,
    leads,
    sent,
    bounced,
    unsubscribed,
    replyRate: sent > 0 ? replied / sent : 0,
    openRate: sent > 0 ? opened / sent : 0,
    leadsViaReferral,
  };
}

export interface WeeklyTrendPoint {
  weekStart: string; // ISO datum (maandag)
  sent: number;
  replied: number;
  leads: number;
}

export async function weeklyTrend(tenantId: string, weeks: number): Promise<WeeklyTrendPoint[]> {
  const points: WeeklyTrendPoint[] = [];
  const now = new Date();
  const monday = new Date(now);
  monday.setUTCDate(monday.getUTCDate() - ((monday.getUTCDay() + 6) % 7));
  monday.setUTCHours(0, 0, 0, 0);
  for (let i = weeks - 1; i >= 0; i--) {
    const start = new Date(monday.getTime() - i * 7 * 86400_000);
    const end = new Date(start.getTime() + 7 * 86400_000);
    const [sent, replied, leads] = await Promise.all([
      prisma.activity.count({ where: { tenantId, type: 'EMAIL_SENT', occurredAt: { gte: start, lt: end } } }),
      prisma.activity.count({ where: { tenantId, type: 'EMAIL_REPLIED', occurredAt: { gte: start, lt: end } } }),
      prisma.lead.count({ where: { tenantId, createdAt: { gte: start, lt: end } } }),
    ]);
    points.push({ weekStart: start.toISOString().slice(0, 10), sent, replied, leads });
  }
  return points;
}

export interface DataHealthSummary {
  totalContacts: number;
  validPercent: number;
  cleanedThisMonth: number;
  lastRun: { ranAt: Date; reportJson: unknown } | null;
}

export async function dataHealthSummary(tenantId: string): Promise<DataHealthSummary> {
  const [total, valid] = await Promise.all([
    prisma.contact.count({ where: { tenantId } }),
    prisma.contact.count({ where: { tenantId, emailStatus: 'VALID' } }),
  ]);
  const monthStart = new Date();
  monthStart.setUTCDate(1);
  monthStart.setUTCHours(0, 0, 0, 0);
  const runs = await prisma.dataHealthRun.findMany({
    where: { tenantId },
    orderBy: { ranAt: 'desc' },
    take: 12,
  });
  const cleanedThisMonth = runs
    .filter((r) => r.ranAt >= monthStart)
    .reduce((sum, r) => sum + r.newInvalid + r.bouncesRemoved + r.suppressed, 0);
  return {
    totalContacts: total,
    validPercent: total > 0 ? Math.round((valid / total) * 100) : 0,
    cleanedThisMonth,
    lastRun: runs[0] ? { ranAt: runs[0].ranAt, reportJson: runs[0].reportJson } : null,
  };
}

/** Branchegemiddelde reply-rate uit de TemplateStat-bibliotheek (voor het waarderapport). */
export async function industryAvgReplyRate(industry: string): Promise<number | null> {
  const stats = await prisma.templateStat.aggregate({
    where: { industry, sentCount: { gte: 200 } },
    _sum: { sentCount: true, replyCount: true },
  });
  const sent = stats._sum.sentCount ?? 0;
  const replies = stats._sum.replyCount ?? 0;
  return sent >= 200 ? replies / sent : null;
}
