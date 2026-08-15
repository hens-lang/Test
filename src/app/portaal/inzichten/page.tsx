// Inzichten & Marktbeeld (klant): volledig geanalyseerde data — segmenten,
// bezwaren, timing, benchmark en trends. Het product is de conclusie, niet de grafiek.
import { requireClient } from '@/lib/auth';
import { prisma } from '@/lib/db';
import { tenantDb } from '@/lib/tenancy';
import { industryAvgReplyRate } from '@/core/stats';
import { computeTrends, MIN_TREND_SNAPSHOTS, type SegmentStat } from '@/jobs/insights';
import type { ObjectionStats } from '@/core/objections';
import { Card, Badge, StatTile } from '@/components/ui';

export const dynamic = 'force-dynamic';

const DIM_LABELS: Record<string, string> = {
  branche: 'Per branche', functiegroep: 'Per functiegroep', grootte: 'Per bedrijfsgrootte', regio: 'Per regio',
};
const DAY_NAMES = ['ma', 'di', 'wo', 'do', 'vr', 'za', 'zo'];

export default async function InzichtenPage() {
  const session = await requireClient();
  const db = tenantDb(session.tenantId);
  const tenant = await prisma.tenant.findUniqueOrThrow({ where: { id: session.tenantId } });
  const snapshots = await db.insightSnapshot.findMany({ orderBy: { period: 'desc' }, take: 12 });
  const latest = snapshots[0];
  const benchmark = tenant.industry ? await industryAvgReplyRate(tenant.industry) : null;

  if (!latest) {
    return (
      <div className="space-y-4">
        <h1 className="text-xl font-bold">Inzichten</h1>
        <p className="text-gray-500">
          De eerste analyse wordt gemaakt zodra er een maand campagnedata is — vanaf dat moment groeit hier elke maand het beeld van uw markt.
        </p>
      </div>
    );
  }

  const segments = (latest.segmentStats as unknown as SegmentStat[]).filter((s) => s.sent >= 5);
  const objections = latest.objectionClusters as unknown as ObjectionStats[];
  const conclusions = latest.conclusions as unknown as string[];
  const timing = latest.timingStats as Record<string, number>;
  const maxTiming = Math.max(1, ...Object.values(timing));
  const replyRate = latest.volumeSent > 0 ? latest.volumeReplies / latest.volumeSent : 0;
  const trends = snapshots.length >= 2 ? computeTrends(snapshots as never) : [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold">Inzichten</h1>
        <p className="text-sm text-gray-500">Analyse over {latest.period} — automatisch bijgewerkt, elke maand scherper.</p>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatTile label="Benaderd" value={latest.volumeSent} />
        <StatTile label="Reply-rate" value={`${(replyRate * 100).toFixed(1)}%`}
          sub={benchmark !== null ? `branchegemiddelde: ${(benchmark * 100).toFixed(1)}%` : undefined} />
        <StatTile label="Leads" value={latest.volumeLeads} />
        <StatTile label="Belcontacten" value={latest.volumeCalls} />
      </div>

      <Card title="Wat wij deze maand over uw markt leerden">
        <ul className="space-y-3">
          {conclusions.map((c, i) => (
            <li key={i} className="flex gap-3 text-sm">
              <span className="mt-0.5 text-brand-600">→</span>
              <span>{c}</span>
            </li>
          ))}
        </ul>
      </Card>

      {(['branche', 'functiegroep', 'grootte', 'regio'] as const).map((dim) => {
        const rows = segments.filter((s) => s.dimension === dim && s.value !== 'Onbekend');
        if (rows.length < 2) return null;
        const maxRate = Math.max(...rows.map((r) => r.replyRate), 0.01);
        return (
          <Card key={dim} title={`${DIM_LABELS[dim]} — wie reageert?`}>
            <div className="space-y-2">
              {rows.sort((a, b) => b.replyRate - a.replyRate).map((s) => (
                <div key={s.value} className="flex items-center gap-3 text-sm">
                  <span className="w-44 shrink-0 truncate">{s.value}</span>
                  <div className="h-4 flex-1 rounded bg-gray-100">
                    <div className="h-4 rounded bg-brand-500" style={{ width: `${(s.replyRate / maxRate) * 100}%` }} />
                  </div>
                  <span className="w-28 shrink-0 text-right text-gray-600">
                    {(s.replyRate * 100).toFixed(1)}% <span className="text-xs text-gray-400">(n={s.sent})</span>
                  </span>
                </div>
              ))}
            </div>
          </Card>
        );
      })}

      {objections.length > 0 && (
        <Card title="Waarom zegt men (nog) nee?">
          <div className="space-y-5">
            {objections.map((o) => (
              <div key={o.cluster}>
                <div className="mb-1 flex items-center gap-2 text-sm">
                  <span className="font-medium">{o.label}</span>
                  <Badge color="blue">{Math.round(o.share * 100)}%</Badge>
                  <span className="text-xs text-gray-400">{o.count}×</span>
                </div>
                {o.quotes[0] && (
                  <blockquote className="mb-1 border-l-2 border-gray-200 pl-3 text-sm italic text-gray-500">
                    &ldquo;{o.quotes[0]}&rdquo;
                  </blockquote>
                )}
                <p className="text-sm text-gray-600">💡 {o.advice}</p>
              </div>
            ))}
          </div>
        </Card>
      )}

      {Object.keys(timing).length > 0 && (
        <Card title="Wanneer komen reacties binnen?">
          <div className="flex items-end gap-3">
            {DAY_NAMES.map((name, i) => {
              const v = timing[String(i + 1)] ?? 0;
              return (
                <div key={name} className="flex flex-1 flex-col items-center gap-1">
                  <div className="w-full rounded-t bg-brand-500" style={{ height: `${v > 0 ? Math.max(6, (v / maxTiming) * 80) : 2}px` }} />
                  <span className="text-xs text-gray-400">{name}</span>
                  <span className="text-[10px] text-gray-500">{v > 0 ? v : ''}</span>
                </div>
              );
            })}
          </div>
        </Card>
      )}

      <Card title="Marktbeeld — verschuift er iets?">
        {snapshots.length < MIN_TREND_SNAPSHOTS ? (
          <p className="text-sm text-gray-500">
            Trends verschijnen na {MIN_TREND_SNAPSHOTS} maanden data ({snapshots.length} van {MIN_TREND_SNAPSHOTS} beschikbaar).
            Elke maand die het platform draait, wordt dit beeld scherper — dit is de kennis die u opbouwt en meeneemt in elk toekomstplan.
          </p>
        ) : (
          <div className="space-y-4">
            {trends.filter((t) => t.points.some((p) => p.value > 0)).map((t) => (
              <div key={t.label} className="flex items-center gap-4 text-sm">
                <span className="w-64 shrink-0">{t.label}</span>
                <div className="flex flex-1 items-end gap-1">
                  {t.points.map((p) => {
                    const max = Math.max(...t.points.map((x) => x.value), 1);
                    return (
                      <div key={p.period} className="flex flex-1 flex-col items-center">
                        <div className="w-full rounded-t bg-brand-500" style={{ height: `${Math.max(3, (p.value / max) * 40)}px` }} title={`${p.period}: ${p.value}`} />
                        <span className="text-[9px] text-gray-400">{p.period.slice(5)}</span>
                      </div>
                    );
                  })}
                </div>
                {t.delta !== null && (
                  <Badge color={t.delta > 0 ? 'green' : t.delta < 0 ? 'red' : 'gray'}>
                    {t.delta > 0 ? '+' : ''}{t.delta}
                  </Badge>
                )}
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
