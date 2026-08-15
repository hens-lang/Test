// Databestand-pagina (§11/§13): gezondheid van het prospectbestand — kern van het data-abonnement.
import { requireClient } from '@/lib/auth';
import { tenantDb } from '@/lib/tenancy';
import { dataHealthSummary } from '@/core/stats';
import { Card, StatTile } from '@/components/ui';

export const dynamic = 'force-dynamic';

export default async function DatabestandPage() {
  const session = await requireClient();
  const health = await dataHealthSummary(session.tenantId);
  const db = tenantDb(session.tenantId);
  const runs = await db.dataHealthRun.findMany({ orderBy: { ranAt: 'desc' }, take: 6 });

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold">Uw databestand</h1>
      <div className="grid grid-cols-3 gap-4">
        <StatTile label="Contacten" value={health.totalContacts} />
        <StatTile label="Gevalideerd" value={`${health.validPercent}%`} />
        <StatTile label="Opgeschoond deze maand" value={health.cleanedThisMonth} />
      </div>

      <Card title="Maandelijkse datacontroles">
        {runs.length === 0 && <p className="text-sm text-gray-500">Nog geen controle uitgevoerd — de eerste run staat gepland.</p>}
        <div className="space-y-4">
          {runs.map((r) => {
            const report = r.reportJson as { samenvatting?: string };
            return (
              <div key={r.id} className="rounded-lg border border-gray-100 p-4">
                <div className="mb-1 text-sm font-medium">{r.ranAt.toLocaleDateString('nl-NL', { day: 'numeric', month: 'long', year: 'numeric' })}</div>
                <p className="text-sm text-gray-600">{report.samenvatting ?? `${r.contactsChecked} contacten gecontroleerd.`}</p>
              </div>
            );
          })}
        </div>
      </Card>
    </div>
  );
}
