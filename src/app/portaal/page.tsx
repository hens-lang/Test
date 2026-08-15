// Klantdashboard-overzicht (§11): funnel, stat-tegels, trend, actieve campagnes.
import { requireClient } from '@/lib/auth';
import { tenantDb } from '@/lib/tenancy';
import { funnelStats, weeklyTrend } from '@/core/stats';
import { Card, StatTile, Badge, statusColor } from '@/components/ui';

export const dynamic = 'force-dynamic';

export default async function PortaalOverzicht() {
  const session = await requireClient();
  const tenantId = session.tenantId;
  const db = tenantDb(tenantId);

  const weekAgo = new Date(Date.now() - 7 * 86400_000);
  const [total, week, trend, campaigns] = await Promise.all([
    funnelStats(tenantId),
    funnelStats(tenantId, weekAgo),
    weeklyTrend(tenantId, 8),
    db.campaign.findMany({ where: { status: { in: ['ACTIVE', 'PAUSED', 'REVIEW'] } } }),
  ]);
  const maxSent = Math.max(1, ...trend.map((t) => t.sent));

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold">Overzicht</h1>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatTile label="Leads deze week" value={week.leads} sub={`totaal: ${total.leads}`} />
        <StatTile label="Reply-rate" value={`${(total.replyRate * 100).toFixed(1)}%`} />
        <StatTile label="Verzonden deze week" value={week.sent} sub={`totaal: ${total.sent}`} />
        <StatTile label="Leads via doorverwijzing" value={total.leadsViaReferral} />
      </div>

      <Card title="Funnel">
        <div className="grid grid-cols-4 gap-4 text-center">
          {[
            ['Benaderd', total.approached],
            ['Geopend*', total.opened],
            ['Gereageerd', total.replied],
            ['Leads', total.leads],
          ].map(([label, value]) => (
            <div key={label as string}>
              <div className="text-2xl font-bold">{value}</div>
              <div className="text-sm text-gray-500">{label}</div>
            </div>
          ))}
        </div>
        <p className="mt-4 text-xs text-gray-400">
          * Open-rates zijn indicatief: privacy-maatregelen van mailproviders maken ze onbetrouwbaar. Wij sturen op reacties en leads.
        </p>
      </Card>

      <Card title="Trend per week (verzonden)">
        <div className="flex h-32 items-end gap-2">
          {trend.map((t) => (
            <div key={t.weekStart} className="flex flex-1 flex-col items-center gap-1">
              <div className="w-full rounded-t bg-brand-500" style={{ height: `${(t.sent / maxSent) * 100}%`, minHeight: t.sent > 0 ? 4 : 0 }} />
              <div className="text-[10px] text-gray-400">{t.weekStart.slice(5)}</div>
              <div className="text-[10px] text-gray-500">{t.leads > 0 ? `${t.leads} lead(s)` : ''}</div>
            </div>
          ))}
        </div>
      </Card>

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
    </div>
  );
}
