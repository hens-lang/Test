// Abonnementen & plannen (§13) + facturatie-export.
import { prisma } from '@/lib/db';
import { requireStaff } from '@/lib/auth';
import { Card, Table, Badge, Button, Input } from '@/components/ui';
import { createPlan, createSubscription } from '../actions';

export const dynamic = 'force-dynamic';

export default async function AbonnementenPage() {
  await requireStaff();
  const [plans, subs, tenants] = await Promise.all([
    prisma.plan.findMany({ where: { active: true } }),
    prisma.subscription.findMany({ include: { tenant: true, plan: true } }),
    prisma.tenant.findMany({ orderBy: { name: 'asc' } }),
  ]);
  const mrr = subs
    .filter((s) => s.status === 'ACTIVE')
    .reduce((sum, s) => sum + (s.priceOverrideCents ?? s.plan.monthlyPriceCents), 0);

  return (
    <div className="max-w-4xl space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Abonnementen</h1>
        <div className="flex items-center gap-4">
          <span className="text-sm">Totale MRR: <strong>€ {(mrr / 100).toFixed(0)}</strong></span>
          <a href="/api/facturatie" className="text-sm text-brand-600 hover:underline">Facturatie-export (CSV) ↓</a>
        </div>
      </div>

      <Card title="Actieve abonnementen">
        <Table headers={['Klant', 'Plan', 'Type', 'Status', 'Prijs/maand']}>
          {subs.map((s) => (
            <tr key={s.id}>
              <td className="px-4 py-3 font-medium">{s.tenant.name}</td>
              <td className="px-4 py-3">{s.plan.name}</td>
              <td className="px-4 py-3"><Badge color={s.plan.type === 'DATA_ONLY' ? 'blue' : 'green'}>{s.plan.type}</Badge></td>
              <td className="px-4 py-3"><Badge color={s.status === 'ACTIVE' ? 'green' : 'orange'}>{s.status}</Badge></td>
              <td className="px-4 py-3">€ {((s.priceOverrideCents ?? s.plan.monthlyPriceCents) / 100).toFixed(0)}{s.priceOverrideCents != null && ' (afwijkend)'}</td>
            </tr>
          ))}
        </Table>
        <form action={createSubscription} className="mt-4 grid grid-cols-4 items-end gap-3">
          <div>
            <label className="mb-1 block text-xs">Klant</label>
            <select name="tenantId" className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm">
              {tenants.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs">Plan</label>
            <select name="planId" className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm">
              {plans.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </div>
          <div><label className="mb-1 block text-xs">Afwijkende prijs (€, optioneel)</label><Input name="priceOverride" type="number" /></div>
          <Button type="submit" variant="secondary">Koppelen</Button>
        </form>
      </Card>

      <Card title="Plannen">
        <Table headers={['Plan', 'Type', 'Prijs/maand', 'Setup', 'Incl. prospects', 'Incl. mailboxen']}>
          {plans.map((p) => (
            <tr key={p.id}>
              <td className="px-4 py-3 font-medium">{p.name}</td>
              <td className="px-4 py-3"><Badge color={p.type === 'DATA_ONLY' ? 'blue' : 'green'}>{p.type}</Badge></td>
              <td className="px-4 py-3">€ {(p.monthlyPriceCents / 100).toFixed(0)}</td>
              <td className="px-4 py-3">€ {(p.setupFeeCents / 100).toFixed(0)}</td>
              <td className="px-4 py-3">{p.includedActiveProspects}</td>
              <td className="px-4 py-3">{p.includedMailboxes}</td>
            </tr>
          ))}
        </Table>
        <form action={createPlan} className="mt-4 grid grid-cols-6 items-end gap-3">
          <div><label className="mb-1 block text-xs">Naam</label><Input name="name" required /></div>
          <div>
            <label className="mb-1 block text-xs">Type</label>
            <select name="type" className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm">
              <option value="CAMPAIGN">CAMPAIGN</option>
              <option value="DATA_ONLY">DATA_ONLY</option>
            </select>
          </div>
          <div><label className="mb-1 block text-xs">Prijs €/mnd</label><Input name="monthlyPrice" type="number" required /></div>
          <div><label className="mb-1 block text-xs">Setup €</label><Input name="setupFee" type="number" defaultValue={0} /></div>
          <div><label className="mb-1 block text-xs">Incl. prospects</label><Input name="includedActiveProspects" type="number" defaultValue={500} /></div>
          <Button type="submit" variant="secondary">Plan toevoegen</Button>
        </form>
      </Card>
    </div>
  );
}
