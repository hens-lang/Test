import Link from 'next/link';
import { prisma } from '@/lib/db';
import { requireStaff } from '@/lib/auth';
import { Card, Table, Badge, Button, Input, statusColor } from '@/components/ui';
import { createCampaign } from '../actions';

export const dynamic = 'force-dynamic';

export default async function CampagnesPage() {
  await requireStaff();
  const [campaigns, tenants] = await Promise.all([
    prisma.campaign.findMany({
      include: {
        tenant: true,
        _count: { select: { enrollments: true, sequenceSteps: true, leads: true } },
      },
      orderBy: { createdAt: 'desc' },
    }),
    prisma.tenant.findMany({ orderBy: { name: 'asc' } }),
  ]);

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold">Campagnes</h1>
      <Table headers={['Campagne', 'Klant', 'Status', 'Stappen', 'Enrollments', 'Leads', '']}>
        {campaigns.map((c) => (
          <tr key={c.id}>
            <td className="px-4 py-3 font-medium">{c.name}</td>
            <td className="px-4 py-3">{c.tenant.name}</td>
            <td className="px-4 py-3"><Badge color={statusColor(c.status)}>{c.status}</Badge></td>
            <td className="px-4 py-3">{c._count.sequenceSteps}</td>
            <td className="px-4 py-3">{c._count.enrollments}</td>
            <td className="px-4 py-3">{c._count.leads}</td>
            <td className="px-4 py-3"><Link className="text-brand-600 hover:underline" href={`/beheer/campagnes/${c.id}`}>Openen →</Link></td>
          </tr>
        ))}
      </Table>

      <Card title="Nieuwe campagne">
        <form action={createCampaign} className="grid max-w-2xl grid-cols-2 gap-4">
          <div>
            <label className="mb-1 block text-sm">Klant</label>
            <select name="tenantId" className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm">
              {tenants.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
            </select>
          </div>
          <div><label className="mb-1 block text-sm">Naam</label><Input name="name" required /></div>
          <div className="col-span-2"><label className="mb-1 block text-sm">Propositie (context voor AI)</label><Input name="proposition" /></div>
          <div><label className="mb-1 block text-sm">Verzendvenster start</label><Input name="sendWindowStart" defaultValue="08:30" /></div>
          <div><label className="mb-1 block text-sm">Verzendvenster einde</label><Input name="sendWindowEnd" defaultValue="17:00" /></div>
          <div><label className="mb-1 block text-sm">Dagcap campagne (optioneel)</label><Input name="dailyCampaignCap" type="number" /></div>
          <div className="col-span-2"><Button type="submit">Campagne aanmaken</Button></div>
        </form>
      </Card>
    </div>
  );
}
