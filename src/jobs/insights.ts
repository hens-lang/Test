// Marktintelligentie-laag: maandelijkse InsightSnapshot per tenant.
// Verzamelt segmentprestaties, classificatieverdeling, bezwaarclusters, timing
// en belvolume, en schrijft er regelgebaseerde conclusies bij. Dit is de bron
// voor de Inzichten- en Marktbeeld-schermen én de maandrapport-sectie.
import { prisma } from '@/lib/db';
import { aggregateObjections, titleGroup, type ObjectionStats } from '@/core/objections';
import { logger } from '@/lib/logger';

export interface SegmentStat {
  dimension: 'branche' | 'functiegroep' | 'grootte' | 'regio';
  value: string;
  sent: number;
  replies: number;
  leads: number;
  replyRate: number;
}

export interface SnapshotData {
  period: string;
  volumeSent: number;
  volumeReplies: number;
  volumeLeads: number;
  volumeCalls: number;
  segmentStats: SegmentStat[];
  classificationStats: Record<string, number>;
  objectionClusters: ObjectionStats[];
  timingStats: Record<string, number>; // replies per ISO-weekdag (1=ma)
  conclusions: string[];
}

export const MIN_SEGMENT_VOLUME = 10; // onder dit volume geen uitspraak per segment
export const MIN_TREND_SNAPSHOTS = 3;

export function periodOf(d: Date): string {
  return d.toISOString().slice(0, 7);
}

/** Puur en testbaar: segmentstatistieken uit ruwe rijen. */
export function computeSegments(
  rows: { industry: string | null; title: string | null; size: string | null; city: string | null; replied: boolean; lead: boolean }[],
): SegmentStat[] {
  const dims: [SegmentStat['dimension'], (r: (typeof rows)[number]) => string][] = [
    ['branche', (r) => r.industry || 'Onbekend'],
    ['functiegroep', (r) => titleGroup(r.title)],
    ['grootte', (r) => r.size || 'Onbekend'],
    ['regio', (r) => r.city || 'Onbekend'],
  ];
  const out: SegmentStat[] = [];
  for (const [dimension, keyFn] of dims) {
    const buckets = new Map<string, { sent: number; replies: number; leads: number }>();
    for (const r of rows) {
      const key = keyFn(r);
      const b = buckets.get(key) ?? { sent: 0, replies: 0, leads: 0 };
      b.sent += 1;
      if (r.replied) b.replies += 1;
      if (r.lead) b.leads += 1;
      buckets.set(key, b);
    }
    for (const [value, b] of buckets) {
      out.push({ dimension, value, ...b, replyRate: b.sent > 0 ? b.replies / b.sent : 0 });
    }
  }
  return out.sort((a, b) => b.sent - a.sent);
}

/** Regelgebaseerde, geschreven conclusies — het product is de aanbeveling, niet de grafiek. */
export function writeConclusions(data: Omit<SnapshotData, 'conclusions'>): string[] {
  const c: string[] = [];
  const pct = (n: number) => `${(n * 100).toFixed(1)}%`;

  // Beste vs. zwakste segment per dimensie (alleen met voldoende volume).
  for (const dim of ['branche', 'functiegroep', 'grootte', 'regio'] as const) {
    const segs = data.segmentStats.filter((s) => s.dimension === dim && s.sent >= MIN_SEGMENT_VOLUME && s.value !== 'Onbekend');
    if (segs.length >= 2) {
      const sorted = [...segs].sort((a, b) => b.replyRate - a.replyRate);
      const best = sorted[0];
      const worst = sorted[sorted.length - 1];
      if (best.replyRate >= worst.replyRate * 1.5 && best.replyRate > 0) {
        const dimLabel = { branche: 'branche', functiegroep: 'functiegroep', grootte: 'bedrijfsgrootte', regio: 'regio' }[dim];
        c.push(
          `Binnen ${dimLabel} reageert "${best.value}" het best (${pct(best.replyRate)} reply-rate, n=${best.sent}) — ` +
          `${(best.replyRate / Math.max(worst.replyRate, 0.001)).toFixed(1)}× beter dan "${worst.value}" (${pct(worst.replyRate)}). ` +
          `Advies: verschuif volume naar "${best.value}".`,
        );
      }
    }
  }

  // Top-bezwaar met advies.
  const topObjection = data.objectionClusters.filter((o) => o.cluster !== 'ANDERS')[0];
  if (topObjection && topObjection.count >= 3) {
    c.push(
      `Het meest gehoorde bezwaar is "${topObjection.label}" (${pct(topObjection.share)} van de afwijzingen). ${topObjection.advice}`,
    );
  }

  // Timing.
  const days = Object.entries(data.timingStats).filter(([, n]) => n > 0);
  if (days.length >= 3) {
    const dayNames: Record<string, string> = { '1': 'maandag', '2': 'dinsdag', '3': 'woensdag', '4': 'donderdag', '5': 'vrijdag', '6': 'zaterdag', '7': 'zondag' };
    const best = days.sort((a, b) => b[1] - a[1])[0];
    c.push(`De meeste reacties komen op ${dayNames[best[0]] ?? best[0]} binnen — plan belangrijke verzendingen aan het begin van de week daarop af.`);
  }

  // Heractiveringspotentieel.
  const notNow = data.classificationStats['NOT_NOW'] ?? 0;
  if (notNow >= 3) {
    c.push(`${notNow} prospects zeiden "nu niet" — deze groep is warm en hoort in de heractiveringswachtrij in plaats van in de prullenbak.`);
  }

  if (c.length === 0) {
    c.push('Nog onvoldoende volume voor betrouwbare uitspraken per segment — de conclusies verschijnen zodra er meer verzonden en gereageerd is.');
  }
  return c;
}

/** Bouwt (of ververst) de snapshot van een kalendermaand. */
export async function buildSnapshot(tenantId: string, monthStart: Date): Promise<string> {
  const start = new Date(Date.UTC(monthStart.getUTCFullYear(), monthStart.getUTCMonth(), 1));
  const end = new Date(Date.UTC(monthStart.getUTCFullYear(), monthStart.getUTCMonth() + 1, 1));
  const period = periodOf(start);
  const range = { gte: start, lt: end };

  // Per benaderd contact: segmentvelden + of er gereageerd is / een lead uit kwam.
  const sentActivities = await prisma.activity.findMany({
    where: { tenantId, type: 'EMAIL_SENT', occurredAt: range },
    select: { contactId: true },
  });
  const contactIds = [...new Set(sentActivities.map((a) => a.contactId))];
  const [contacts, repliedIds, leadIds, inbound, leads, callCount, replyTimings] = await Promise.all([
    prisma.contact.findMany({
      where: { id: { in: contactIds } },
      select: { id: true, title: true, company: { select: { industry: true, size: true, city: true } } },
    }),
    prisma.activity.findMany({
      where: { tenantId, type: 'EMAIL_REPLIED', occurredAt: range },
      select: { contactId: true },
    }).then((r) => new Set(r.map((x) => x.contactId))),
    prisma.lead.findMany({ where: { tenantId, createdAt: range }, select: { contactId: true } })
      .then((r) => new Set(r.map((x) => x.contactId))),
    prisma.message.findMany({
      where: { tenantId, direction: 'IN', receivedAt: range },
      select: { classifiedAs: true, body: true },
    }),
    prisma.lead.count({ where: { tenantId, createdAt: range } }),
    prisma.activity.count({ where: { tenantId, type: { in: ['CALL_MADE', 'CALL_RESULT'] }, occurredAt: range } }),
    prisma.activity.findMany({
      where: { tenantId, type: 'EMAIL_REPLIED', occurredAt: range },
      select: { occurredAt: true },
    }),
  ]);

  const rows = contacts.map((ct) => ({
    industry: ct.company.industry,
    title: ct.title,
    size: ct.company.size,
    city: ct.company.city,
    replied: repliedIds.has(ct.id),
    lead: leadIds.has(ct.id),
  }));
  const segmentStats = computeSegments(rows);

  const classificationStats: Record<string, number> = {};
  for (const m of inbound) {
    const k = m.classifiedAs ?? 'OTHER';
    classificationStats[k] = (classificationStats[k] ?? 0) + 1;
  }

  const objectionTexts = inbound
    .filter((m) => m.classifiedAs === 'NEGATIVE' || m.classifiedAs === 'NOT_NOW')
    .map((m) => m.body);
  const objectionClusters = aggregateObjections(objectionTexts);

  const timingStats: Record<string, number> = {};
  for (const r of replyTimings) {
    const iso = String(((r.occurredAt.getUTCDay() + 6) % 7) + 1);
    timingStats[iso] = (timingStats[iso] ?? 0) + 1;
  }

  const base = {
    period,
    volumeSent: sentActivities.length,
    volumeReplies: replyTimings.length,
    volumeLeads: leads,
    volumeCalls: callCount,
    segmentStats,
    classificationStats,
    objectionClusters,
    timingStats,
  };
  const conclusions = writeConclusions(base);

  const snapshot = await prisma.insightSnapshot.upsert({
    where: { tenantId_period: { tenantId, period } },
    create: { tenantId, ...base, segmentStats: segmentStats as never, objectionClusters: objectionClusters as never, conclusions },
    update: { ...base, segmentStats: segmentStats as never, objectionClusters: objectionClusters as never, conclusions },
  });
  logger.info({ tenantId, period }, 'insight_snapshot_built');
  return snapshot.id;
}

export async function buildSnapshotsForAllTenants(): Promise<void> {
  const tenants = await prisma.tenant.findMany({ select: { id: true } });
  const lastMonth = new Date();
  lastMonth.setUTCMonth(lastMonth.getUTCMonth() - 1);
  for (const t of tenants) {
    await buildSnapshot(t.id, lastMonth); // vorige maand definitief
    await buildSnapshot(t.id, new Date()); // lopende maand ververst
  }
}

/** Trend: verschil tussen de recentste snapshots (voor het Marktbeeld). */
export interface TrendLine {
  label: string;
  points: { period: string; value: number }[];
  delta: number | null; // laatste t.o.v. voorlaatste, in procentpunt of aantal
}

export function computeTrends(snapshots: { period: string; volumeSent: number; volumeReplies: number; objectionClusters: unknown; classificationStats: unknown }[]): TrendLine[] {
  const sorted = [...snapshots].sort((a, b) => a.period.localeCompare(b.period));
  const lines: TrendLine[] = [];

  const replyRate = sorted.map((s) => ({
    period: s.period,
    value: s.volumeSent > 0 ? (s.volumeReplies / s.volumeSent) * 100 : 0,
  }));
  lines.push({ label: 'Reply-rate (%)', points: replyRate, delta: delta(replyRate) });

  // Bezwaarclusters als aandeel over tijd.
  const clusterNames = new Set<string>();
  for (const s of sorted) {
    for (const o of (s.objectionClusters as ObjectionStats[] | null) ?? []) clusterNames.add(o.label);
  }
  for (const name of clusterNames) {
    const points = sorted.map((s) => {
      const o = ((s.objectionClusters as ObjectionStats[] | null) ?? []).find((x) => x.label === name);
      return { period: s.period, value: o ? Math.round(o.share * 100) : 0 };
    });
    lines.push({ label: `Bezwaar: ${name} (%)`, points, delta: delta(points) });
  }
  return lines;
}

function delta(points: { value: number }[]): number | null {
  if (points.length < 2) return null;
  return Math.round((points[points.length - 1].value - points[points.length - 2].value) * 10) / 10;
}
