import { prisma } from '@/lib/db';
import { requireStaff } from '@/lib/auth';
import { notFound } from 'next/navigation';
import { Card, Button, Input, Textarea, Table, Badge } from '@/components/ui';
import { updateTenant, createUser, runDataHealthNow } from '../../actions';

export const dynamic = 'force-dynamic';

export default async function TenantDetail({ params }: { params: { id: string } }) {
  await requireStaff();
  const tenant = await prisma.tenant.findUnique({
    where: { id: params.id },
    include: {
      users: true,
      dataHealthRuns: { orderBy: { ranAt: 'desc' }, take: 5 },
      subscriptions: { include: { plan: true } },
    },
  });
  if (!tenant) notFound();

  return (
    <div className="max-w-3xl space-y-6">
      <h1 className="text-xl font-bold">{tenant.name}</h1>

      <Card title="Instellingen">
        <form action={updateTenant} className="space-y-4">
          <input type="hidden" name="id" value={tenant.id} />
          <div className="grid grid-cols-2 gap-4">
            <div><label className="mb-1 block text-sm">Branche</label><Input name="industry" defaultValue={tenant.industry ?? ''} /></div>
            <div><label className="mb-1 block text-sm">Merkkleur</label><Input name="brandColor" defaultValue={tenant.brandColor ?? ''} /></div>
            <div><label className="mb-1 block text-sm">Fysiek afzenderadres (verplicht voor verzending)</label><Input name="senderAddress" defaultValue={tenant.senderAddress ?? ''} /></div>
            <div><label className="mb-1 block text-sm">Webhook-URL (notificaties)</label><Input name="webhookUrl" defaultValue={tenant.webhookUrl ?? ''} /></div>
            <div className="col-span-2"><label className="mb-1 block text-sm">Rapportage-ontvangers (komma-gescheiden)</label><Input name="reportRecipients" defaultValue={tenant.reportRecipients ?? ''} /></div>
          </div>
          <div>
            <label className="mb-1 block text-sm">Tone of voice-profiel (voor AI-conceptantwoorden)</label>
            <Textarea name="toneOfVoice" rows={6} defaultValue={tenant.toneOfVoice ?? ''} placeholder="Schrijfstijl, je/u, do's & don'ts, 2-3 voorbeeldmails…" />
          </div>
          <Button type="submit">Opslaan</Button>
        </form>
      </Card>

      <Card title="Gebruikers">
        <Table headers={['Naam', 'E-mail', 'Rol', 'Laatste login']}>
          {tenant.users.map((u) => (
            <tr key={u.id}>
              <td className="px-4 py-3">{u.name}</td>
              <td className="px-4 py-3">{u.email}</td>
              <td className="px-4 py-3"><Badge color="blue">{u.role}</Badge></td>
              <td className="px-4 py-3 text-xs text-gray-500">{u.lastLoginAt?.toLocaleString('nl-NL') ?? 'nooit'}</td>
            </tr>
          ))}
        </Table>
        <form action={createUser} className="mt-4 grid grid-cols-4 items-end gap-3">
          <input type="hidden" name="tenantId" value={tenant.id} />
          <input type="hidden" name="role" value="CLIENT" />
          <div><label className="mb-1 block text-xs">Naam</label><Input name="name" required /></div>
          <div><label className="mb-1 block text-xs">E-mail</label><Input name="email" type="email" required /></div>
          <div><label className="mb-1 block text-xs">Wachtwoord</label><Input name="password" type="password" required minLength={10} /></div>
          <Button type="submit" variant="secondary">Klantlogin toevoegen</Button>
        </form>
      </Card>

      <Card title="Datahygiëne (DataHealthRuns)">
        <form action={runDataHealthNow} className="mb-4">
          <input type="hidden" name="tenantId" value={tenant.id} />
          <Button type="submit" variant="secondary">Nu een DataHealthRun draaien</Button>
        </form>
        <Table headers={['Datum', 'Gecheckt', 'Nieuw ongeldig', 'Bounces', 'Gesupprimeerd']}>
          {tenant.dataHealthRuns.map((r) => (
            <tr key={r.id}>
              <td className="px-4 py-3">{r.ranAt.toLocaleString('nl-NL')}</td>
              <td className="px-4 py-3">{r.contactsChecked}</td>
              <td className="px-4 py-3">{r.newInvalid}</td>
              <td className="px-4 py-3">{r.bouncesRemoved}</td>
              <td className="px-4 py-3">{r.suppressed}</td>
            </tr>
          ))}
        </Table>
      </Card>
    </div>
  );
}
