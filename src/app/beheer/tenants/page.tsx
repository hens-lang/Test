import Link from 'next/link';
import { prisma } from '@/lib/db';
import { requireStaff } from '@/lib/auth';
import { Card, Table, Badge, Button, Input, statusColor } from '@/components/ui';
import { createTenant } from '../actions';

export const dynamic = 'force-dynamic';

export default async function TenantsPage() {
  await requireStaff();
  const tenants = await prisma.tenant.findMany({
    include: {
      subscriptions: { where: { status: { in: ['ACTIVE', 'TRIAL'] } }, include: { plan: true } },
      _count: { select: { contacts: true, campaigns: true, leads: true } },
    },
    orderBy: { createdAt: 'desc' },
  });

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold">Klanten</h1>
      <Table headers={['Klant', 'Plan', 'MRR', 'Prospects', 'Verbruik', 'Campagnes', 'Leads', '']}>
        {tenants.map((t) => {
          const sub = t.subscriptions[0];
          const price = sub ? (sub.priceOverrideCents ?? sub.plan.monthlyPriceCents) / 100 : 0;
          const included = sub?.plan.includedActiveProspects ?? 0;
          const over = included > 0 && t._count.contacts > included;
          return (
            <tr key={t.id}>
              <td className="px-4 py-3 font-medium">{t.name}</td>
              <td className="px-4 py-3">
                {sub ? <Badge color={sub.plan.type === 'DATA_ONLY' ? 'blue' : 'green'}>{sub.plan.name}</Badge> : <Badge>geen</Badge>}
              </td>
              <td className="px-4 py-3">€ {price.toFixed(0)}</td>
              <td className="px-4 py-3">{t._count.contacts}</td>
              <td className="px-4 py-3">
                {included > 0 ? (
                  <Badge color={over ? 'red' : 'green'}>
                    {t._count.contacts}/{included} {over ? '· upsell-signaal' : ''}
                  </Badge>
                ) : '—'}
              </td>
              <td className="px-4 py-3">{t._count.campaigns}</td>
              <td className="px-4 py-3">{t._count.leads}</td>
              <td className="px-4 py-3">
                <Link className="text-brand-600 hover:underline" href={`/beheer/tenants/${t.id}`}>Beheren →</Link>
              </td>
            </tr>
          );
        })}
      </Table>

      <Card title="Nieuwe klant">
        <form action={createTenant} className="grid max-w-2xl grid-cols-2 gap-4">
          <div><label className="mb-1 block text-sm">Naam</label><Input name="name" required /></div>
          <div><label className="mb-1 block text-sm">Branche</label><Input name="industry" placeholder="bijv. logistiek" /></div>
          <div><label className="mb-1 block text-sm">Fysiek afzenderadres</label><Input name="senderAddress" placeholder="Bedrijf BV, Straat 1, 1234 AB Plaats" /></div>
          <div><label className="mb-1 block text-sm">Merkkleur</label><Input name="brandColor" placeholder="#1d4ed8" /></div>
          <div className="col-span-2"><Button type="submit">Klant aanmaken</Button></div>
        </form>
      </Card>
    </div>
  );
}
