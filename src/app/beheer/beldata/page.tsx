// Beldata & inzichten (intern): belexports importeren zodat bellen en mailen
// één tijdlijn vormen, en snapshots handmatig verversen.
import { prisma } from '@/lib/db';
import { requireStaff } from '@/lib/auth';
import { Card, Button, Textarea, StatTile } from '@/components/ui';
import { importCallData, buildSnapshotNow } from '../actions';

export const dynamic = 'force-dynamic';

export default async function BeldataPage({ searchParams }: { searchParams: { tenantId?: string; matched?: string; unmatched?: string } }) {
  await requireStaff();
  const tenants = await prisma.tenant.findMany({ orderBy: { name: 'asc' } });
  const tenantId = searchParams.tenantId || tenants[0]?.id;
  if (!tenantId) return <p>Maak eerst een klant aan.</p>;

  const [calls, snapshots] = await Promise.all([
    prisma.activity.count({ where: { tenantId, type: { in: ['CALL_MADE', 'CALL_RESULT'] } } }),
    prisma.insightSnapshot.findMany({ where: { tenantId }, orderBy: { period: 'desc' }, take: 6 }),
  ]);

  return (
    <div className="max-w-3xl space-y-6">
      <h1 className="text-xl font-bold">Beldata &amp; inzichten</h1>

      <div className="flex flex-wrap gap-2 text-sm">
        {tenants.map((t) => (
          <a key={t.id} href={`/beheer/beldata?tenantId=${t.id}`}
            className={`rounded-full px-3 py-1 ${t.id === tenantId ? 'bg-brand-600 text-white' : 'border border-gray-300 bg-white'}`}>
            {t.name}
          </a>
        ))}
      </div>

      {searchParams.matched && (
        <div className="rounded-lg bg-green-50 p-3 text-sm text-green-800">
          Import verwerkt: {searchParams.matched} gekoppeld, {searchParams.unmatched} niet gevonden (geen match op e-mail of bedrijfsnaam).
        </div>
      )}

      <div className="grid grid-cols-2 gap-4">
        <StatTile label="Belactiviteiten in tijdlijn" value={calls} />
        <StatTile label="Inzicht-snapshots" value={snapshots.length} sub={snapshots[0] ? `laatste: ${snapshots[0].period}` : 'nog geen'} />
      </div>

      <Card title="Belexport importeren (Steam Connect / Belstat)">
        <form action={importCallData} className="space-y-3">
          <input type="hidden" name="tenantId" value={tenantId} />
          <Textarea name="csv" rows={6} required
            placeholder={'email,resultaat,datum,notitie\ncontact@bedrijf0.nl,Afspraak,2026-08-12,Wil in september afspreken\n,Geen gehoor,2026-08-12,'} />
          <p className="text-xs text-gray-500">
            Kolommen: <code>email</code> óf <code>bedrijf</code> (voor de koppeling), <code>resultaat</code>, optioneel <code>datum</code> en <code>notitie</code>.
            Gekoppelde regels verschijnen als belactiviteit op de contact-tijdlijn en tellen mee in de inzichten.
          </p>
          <Button type="submit">Importeren</Button>
        </form>
      </Card>

      <Card title="Snapshot verversen">
        <form action={buildSnapshotNow} className="flex items-center gap-4">
          <input type="hidden" name="tenantId" value={tenantId} />
          <Button type="submit" variant="secondary">Inzichten nu herberekenen</Button>
          <span className="text-xs text-gray-500">Draait normaal automatisch op de 1e van de maand.</span>
        </form>
      </Card>
    </div>
  );
}
