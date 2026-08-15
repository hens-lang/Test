// Template-intelligence (§12): geanonimiseerde, tenant-overstijgende ranglijsten.
import { prisma } from '@/lib/db';
import { requireStaff } from '@/lib/auth';
import { Card, Table, Badge } from '@/components/ui';
import { MIN_SAMPLE_FOR_DISPLAY, isDisplayable } from '@/core/anonymize';

export const dynamic = 'force-dynamic';

export default async function BibliotheekPage() {
  await requireStaff();
  const stats = await prisma.templateStat.findMany({ orderBy: { replyCount: 'desc' }, take: 200 });
  const industries = [...new Set(stats.map((s) => s.industry))];
  const displayable = stats.filter((s) => isDisplayable(s.sentCount));

  return (
    <div className="max-w-4xl space-y-6">
      <h1 className="text-xl font-bold">Templatebibliotheek</h1>
      <p className="text-sm text-gray-500">
        Geanonimiseerde prestatiedata over alle klanten heen — variabelen zijn geneutraliseerd, statistieken verschijnen
        pas vanaf n ≥ {MIN_SAMPLE_FOR_DISPLAY} verzonden. Deze bibliotheek is een kernasset van LINK.
      </p>

      {industries.map((industry) => {
        const rows = displayable.filter((s) => s.industry === industry);
        if (rows.length === 0) return null;
        return (
          <Card key={industry} title={`Branche: ${industry}`}>
            <Table headers={['Type', 'Template', 'Verzonden', 'Reply-rate', 'Positive-rate']}>
              {rows.map((s) => (
                <tr key={s.id}>
                  <td className="px-4 py-3"><Badge color="blue">{s.kind}</Badge></td>
                  <td className="px-4 py-3 font-mono text-xs">{s.textSample.slice(0, 90)}</td>
                  <td className="px-4 py-3">{s.sentCount}</td>
                  <td className="px-4 py-3">{((s.replyCount / Math.max(1, s.sentCount)) * 100).toFixed(1)}%</td>
                  <td className="px-4 py-3">{((s.positiveCount / Math.max(1, s.sentCount)) * 100).toFixed(1)}%</td>
                </tr>
              ))}
            </Table>
          </Card>
        );
      })}
      {displayable.length === 0 && (
        <p className="text-gray-500">
          Nog onvoldoende volume (n ≥ {MIN_SAMPLE_FOR_DISPLAY} per template) om statistieken te tonen.
          {stats.length > 0 && ` Er zijn al ${stats.length} templates in de bibliotheek.`}
        </p>
      )}
    </div>
  );
}
