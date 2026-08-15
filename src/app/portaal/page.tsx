// Klantdashboard — gebouwd rond de intelligentielaag: resultaten, conclusies,
// bezwaren en marktbeeld op één scherm. Cijfers uit de gedeelde query-laag en
// de InsightSnapshots (zelfde bron als het maandrapport).
import Link from 'next/link';
import { requireClient } from '@/lib/auth';
import { prisma } from '@/lib/db';
import { tenantDb } from '@/lib/tenancy';
import { funnelStats, weeklyTrend, dataHealthSummary, industryAvgReplyRate } from '@/core/stats';
import { computeTrends, MIN_TREND_SNAPSHOTS } from '@/jobs/insights';
import type { ObjectionStats } from '@/core/objections';
import { Card, Badge, statusColor } from '@/components/ui';

export const dynamic = 'force-dynamic';

// Grafiekkleuren (gevalideerd paar): blauw = verzonden, amber = reacties.
const SERIES = { sent: '#2563eb', replies: '#d97706' };

function DeltaChip({ value, suffix = '' }: { value: number | null; suffix?: string }) {
  if (value === null || value === 0) return null;
  const up = value > 0;
  return (
    <span className={`ml-2 inline-block rounded-full px-2 py-0.5 text-xs font-medium ${up ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
      {up ? '▲' : '▼'} {Math.abs(value)}{suffix}
    </span>
  );
}

function Kpi({ label, value, delta, deltaSuffix, sub }: { label: string; value: string | number; delta?: number | null; deltaSuffix?: string; sub?: string }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <div className="text-sm text-gray-500">{label}</div>
      <div className="mt-1 flex items-baseline text-3xl font-bold tabular-nums">
        {value}
        <DeltaChip value={delta ?? null} suffix={deltaSuffix} />
      </div>
      {sub && <div className="mt-1 text-xs text-gray-400">{sub}</div>}
    </div>
  );
}

export default async function PortaalDashboard() {
  const session = await requireClient();
  const tenantId = session.tenantId;
  const db = tenantDb(tenantId);
  const tenant = await prisma.tenant.findUniqueOrThrow({
    where: { id: tenantId },
    include: { subscriptions: { where: { status: { in: ['ACTIVE', 'TRIAL'] } }, include: { plan: true } } },
  });
  const isDataOnly = tenant.subscriptions[0]?.plan.type === 'DATA_ONLY';

  const now = new Date();
  const monthStart = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1));
  const prevMonthStart = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth() - 1, 1));

  const [thisMonth, prevMonth, trend, snapshots, benchmark, leads, campaigns, health] = await Promise.all([
    funnelStats(tenantId, monthStart),
    funnelStats(tenantId, prevMonthStart, monthStart),
    weeklyTrend(tenantId, 12),
    db.insightSnapshot.findMany({ orderBy: { period: 'desc' }, take: 12 }),
    tenant.industry ? industryAvgReplyRate(tenant.industry) : null,
    db.lead.findMany({ include: { contact: { include: { company: true } } }, orderBy: { createdAt: 'desc' }, take: 5 }),
    db.campaign.findMany({ where: { status: { in: ['ACTIVE', 'PAUSED', 'REVIEW'] } } }),
    dataHealthSummary(tenantId),
  ]);

  const latest = snapshots[0];
  const conclusions = ((latest?.conclusions as string[] | null) ?? []).slice(0, 3);
  const objections = ((latest?.objectionClusters as unknown as ObjectionStats[] | null) ?? []).filter((o) => o.cluster !== 'ANDERS').slice(0, 3);
  const marktTrends = snapshots.length >= 2 ? computeTrends(snapshots as never) : [];
  const replyTrend = marktTrends.find((t) => t.label.startsWith('Reply-rate'));
  const biggestShift = marktTrends
    .filter((t) => t.label.startsWith('Bezwaar') && t.delta !== null)
    .sort((a, b) => Math.abs(b.delta!) - Math.abs(a.delta!))[0];

  const replyRatePP = benchmark !== null ? Math.round((thisMonth.replyRate - benchmark) * 1000) / 10 : null;
  const maxTrend = Math.max(1, ...trend.map((t) => Math.max(t.sent, t.replied)));

  return (
    <div className="space-y-6">
      <div className="flex items-baseline justify-between">
        <div>
          <h1 className="text-xl font-bold">Dashboard</h1>
          <p className="text-sm text-gray-500">
            {now.toLocaleDateString('nl-NL', { month: 'long', year: 'numeric' })} — live bijgewerkt
          </p>
        </div>
        <Link href="/portaal/maandrapport" className="text-sm text-brand-600 hover:underline">Volledig maandrapport →</Link>
      </div>

      {/* KPI-rij met maanddelta's */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Kpi label="Leads deze maand" value={thisMonth.leads} delta={thisMonth.leads - prevMonth.leads} sub={`vorige maand: ${prevMonth.leads}`} />
        <Kpi
          label="Reply-rate"
          value={`${(thisMonth.replyRate * 100).toFixed(1)}%`}
          delta={replyRatePP}
          deltaSuffix=" pt"
          sub={benchmark !== null ? `t.o.v. branchegemiddelde ${(benchmark * 100).toFixed(1)}%` : 'branchegemiddelde volgt'}
        />
        <Kpi label="Benaderde prospects" value={thisMonth.approached} delta={thisMonth.approached - prevMonth.approached} sub={`vorige maand: ${prevMonth.approached}`} />
        {isDataOnly
          ? <Kpi label="Bestand gevalideerd" value={`${health.validPercent}%`} sub={`${health.totalContacts} contacten`} />
          : <Kpi label="Leads via doorverwijzing" value={thisMonth.leadsViaReferral} sub="warmste ingang die er is" />}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Conclusies — het hart van het dashboard */}
        <Card title="Wat wij over uw markt leerden">
          {conclusions.length > 0 ? (
            <ul className="space-y-3">
              {conclusions.map((c, i) => (
                <li key={i} className="flex gap-3 text-sm">
                  <span className="mt-0.5 text-brand-600">→</span>
                  <span>{c}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-gray-500">De eerste analyse verschijnt na een maand campagnedata.</p>
          )}
          {!isDataOnly && (
            <Link href="/portaal/inzichten" className="mt-4 inline-block text-sm text-brand-600 hover:underline">
              Alle inzichten en segmenten →
            </Link>
          )}
        </Card>

        {/* Funnel deze maand */}
        <Card title="Funnel deze maand">
          <div className="grid h-full grid-cols-4 items-center gap-4 text-center">
            {[
              ['Benaderd', thisMonth.approached],
              ['Geopend*', thisMonth.opened],
              ['Gereageerd', thisMonth.replied],
              ['Leads', thisMonth.leads],
            ].map(([label, value]) => (
              <div key={label as string}>
                <div className="text-2xl font-bold tabular-nums">{value}</div>
                <div className="text-sm text-gray-500">{label}</div>
              </div>
            ))}
          </div>
          <p className="mt-4 text-xs text-gray-400">* Open-rates zijn indicatief (privacy-proxies) — wij sturen op reacties en leads.</p>
        </Card>
      </div>

      {/* Trend: 12 weken, twee reeksen op één schaal */}
      <Card title="Verloop per week">
        <div className="mb-3 flex gap-4 text-xs text-gray-600">
          <span className="flex items-center gap-1.5"><span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: SERIES.sent }} /> Verzonden</span>
          <span className="flex items-center gap-1.5"><span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: SERIES.replies }} /> Reacties</span>
        </div>
        <div className="flex items-end gap-2">
          {trend.map((t) => (
            <div key={t.weekStart} className="flex flex-1 flex-col items-center gap-1" title={`Week van ${t.weekStart}: ${t.sent} verzonden, ${t.replied} reacties, ${t.leads} leads`}>
              <div className="flex w-full items-end justify-center gap-0.5">
                <div className="w-2/5 rounded-t" style={{ background: SERIES.sent, height: `${t.sent > 0 ? Math.max(5, (t.sent / maxTrend) * 96) : 2}px` }} />
                <div className="w-2/5 rounded-t" style={{ background: SERIES.replies, height: `${t.replied > 0 ? Math.max(5, (t.replied / maxTrend) * 96) : 2}px` }} />
              </div>
              <span className="text-[10px] text-gray-400">{t.weekStart.slice(5)}</span>
              <span className="text-[10px] font-medium text-gray-500">{t.leads > 0 ? `${t.leads} lead${t.leads > 1 ? 's' : ''}` : ''}</span>
            </div>
          ))}
        </div>
      </Card>

      {!isDataOnly && (
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Topbezwaren */}
          <Card title="Waarom zegt men (nog) nee?">
            {objections.length > 0 ? (
              <div className="space-y-3">
                {objections.map((o) => (
                  <div key={o.cluster} title={o.quotes[0] ? `"${o.quotes[0]}"` : undefined}>
                    <div className="mb-1 flex items-center justify-between text-sm">
                      <span>{o.label}</span>
                      <span className="tabular-nums text-gray-500">{Math.round(o.share * 100)}%</span>
                    </div>
                    <div className="h-3 rounded bg-gray-100">
                      <div className="h-3 rounded bg-brand-500" style={{ width: `${Math.round(o.share * 100)}%` }} />
                    </div>
                  </div>
                ))}
                <Link href="/portaal/inzichten" className="inline-block text-sm text-brand-600 hover:underline">Bezwaren met citaten en advies →</Link>
              </div>
            ) : (
              <p className="text-sm text-gray-500">Nog geen afwijzingen om te analyseren — dat is ook een antwoord.</p>
            )}
          </Card>

          {/* Marktbeeld-samenvatting */}
          <Card title="Marktbeeld">
            {snapshots.length >= MIN_TREND_SNAPSHOTS && replyTrend ? (
              <div className="space-y-4 text-sm">
                <div className="flex items-center justify-between">
                  <span>Reply-rate over {replyTrend.points.length} maanden</span>
                  <DeltaChip value={replyTrend.delta} suffix=" pt" />
                </div>
                <div className="flex items-end gap-1.5">
                  {replyTrend.points.map((p) => {
                    const max = Math.max(...replyTrend.points.map((x) => x.value), 1);
                    return (
                      <div key={p.period} className="flex flex-1 flex-col items-center gap-1" title={`${p.period}: ${p.value.toFixed(1)}%`}>
                        <div className="w-full rounded-t bg-brand-500" style={{ height: `${Math.max(5, (p.value / max) * 56)}px` }} />
                        <span className="text-[10px] text-gray-400">{p.period.slice(5)}</span>
                      </div>
                    );
                  })}
                </div>
                {biggestShift && (
                  <p className="border-t border-gray-100 pt-3 text-gray-600">
                    Grootste verschuiving: <strong>{biggestShift.label.replace('Bezwaar: ', '').replace(' (%)', '')}</strong>
                    {' '}{biggestShift.delta! > 0 ? 'steeg' : 'daalde'} {Math.abs(biggestShift.delta!)} procentpunt — dit zegt iets over waar uw markt heen beweegt.
                  </p>
                )}
              </div>
            ) : (
              <p className="text-sm text-gray-500">
                Trends verschijnen na {MIN_TREND_SNAPSHOTS} maanden data ({snapshots.length} beschikbaar). Elke maand wordt dit beeld scherper.
              </p>
            )}
          </Card>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Recente leads */}
        <Card title="Recente leads">
          {leads.length > 0 ? (
            <ul className="divide-y divide-gray-100">
              {leads.map((l) => (
                <li key={l.id} className="flex items-center gap-3 py-2.5 text-sm">
                  <div className="min-w-0 flex-1">
                    <span className="font-medium">{l.contact.firstName} {l.contact.lastName}</span>
                    <span className="text-gray-400"> · {l.contact.company.name}</span>
                  </div>
                  {l.viaReferral && <Badge color="blue">doorverwijzing</Badge>}
                  <span className="text-xs text-gray-400">{l.createdAt.toLocaleDateString('nl-NL')}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-gray-500">Nog geen leads — zodra er een positieve reactie binnenkomt, staat hij hier.</p>
          )}
          {!isDataOnly && <Link href="/portaal/leads" className="mt-3 inline-block text-sm text-brand-600 hover:underline">Alle leads met conversaties →</Link>}
        </Card>

        {/* Actieve campagnes of databestand */}
        {isDataOnly ? (
          <Card title="Uw databestand">
            <ul className="space-y-2 text-sm">
              <li className="flex justify-between"><span>Contacten</span><strong className="tabular-nums">{health.totalContacts}</strong></li>
              <li className="flex justify-between"><span>Gevalideerd</span><strong className="tabular-nums">{health.validPercent}%</strong></li>
              <li className="flex justify-between"><span>Opgeschoond deze maand</span><strong className="tabular-nums">{health.cleanedThisMonth}</strong></li>
            </ul>
            <Link href="/portaal/databestand" className="mt-3 inline-block text-sm text-brand-600 hover:underline">Alle datacontroles →</Link>
          </Card>
        ) : (
          <Card title="Actieve campagnes">
            <ul className="space-y-2">
              {campaigns.map((c) => (
                <li key={c.id} className="flex items-center gap-3 text-sm">
                  <span className="font-medium">{c.name}</span>
                  <Badge color={statusColor(c.status)}>{c.status}</Badge>
                </li>
              ))}
              {campaigns.length === 0 && <li className="text-sm text-gray-500">Geen actieve campagnes.</li>}
            </ul>
          </Card>
        )}
      </div>
    </div>
  );
}
