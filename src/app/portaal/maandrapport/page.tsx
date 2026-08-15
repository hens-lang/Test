// "Uw maand in cijfers" (§13) — dashboardversie van het maandelijkse waarderapport.
// Gebruikt exact dezelfde opbouw/query-laag als de rapportmail.
import { requireClient } from '@/lib/auth';
import { buildMonthlyValueReport } from '@/jobs/reports';

export const dynamic = 'force-dynamic';

export default async function MaandrapportPage() {
  const session = await requireClient();
  const report = await buildMonthlyValueReport(session.tenantId);
  return (
    <div>
      <h1 className="mb-4 text-xl font-bold">Uw maand in cijfers</h1>
      <div className="overflow-hidden rounded-xl border border-gray-200" dangerouslySetInnerHTML={{ __html: report.html }} />
    </div>
  );
}
