// Domeinen & mailboxen (§7a/§7b): onboarding-wizard met DNS-records, checks en warm-up.
import { prisma } from '@/lib/db';
import { requireStaff, getSession } from '@/lib/auth';
import { Card, Table, Badge, Button, Input, statusColor } from '@/components/ui';
import { requiredDnsRecords } from '@/core/dns-check';
import { createDomain, checkDomainNow, createMailbox, setMaxCap } from '../actions';

export const dynamic = 'force-dynamic';

export default async function InfraPage() {
  await requireStaff();
  const session = await getSession();
  const [domains, tenants] = await Promise.all([
    prisma.sendingDomain.findMany({ include: { tenant: true, mailboxes: true } }),
    prisma.tenant.findMany({ orderBy: { name: 'asc' } }),
  ]);

  return (
    <div className="max-w-4xl space-y-6">
      <h1 className="text-xl font-bold">Domeinen &amp; mailboxen</h1>

      {domains.map((d) => (
        <Card key={d.id} title={`${d.domain} — ${d.tenant.name}`}>
          <div className="mb-3 flex items-center gap-2">
            <Badge color={statusColor(d.status)}>{d.status}</Badge>
            <Badge color={d.spfOk ? 'green' : 'red'}>SPF {d.spfOk ? '✓' : '✗'}</Badge>
            <Badge color={d.dkimOk ? 'green' : 'red'}>DKIM {d.dkimOk ? '✓' : '✗'}</Badge>
            <Badge color={d.dmarcOk ? 'green' : 'orange'}>DMARC {d.dmarcOk ? '✓' : '✗'}</Badge>
            <Badge color={d.mxOk ? 'green' : 'orange'}>MX {d.mxOk ? '✓' : '✗'}</Badge>
            <form action={checkDomainNow} className="ml-auto">
              <input type="hidden" name="domainId" value={d.id} />
              <Button type="submit" variant="secondary">Check nu</Button>
            </form>
          </div>
          {(!d.spfOk || !d.dkimOk) && (
            <p className="mb-3 rounded-lg bg-red-50 p-3 text-sm text-red-700">
              Zonder geldige SPF+DKIM verstuurt dit domein niets — hard geblokkeerd in de verzendjob.
            </p>
          )}

          <details className="mb-4">
            <summary className="cursor-pointer text-sm font-medium text-brand-600">Te zetten DNS-records (onboarding)</summary>
            <div className="mt-3 space-y-2">
              {requiredDnsRecords(d.domain, d.dkimSelector || 'default', '_spf.google.com', 'track.linkgrp.nl').map((r, i) => (
                <div key={i} className="rounded-lg bg-gray-50 p-3 font-mono text-xs">
                  <div className="mb-1 font-sans text-gray-500">{r.uitleg}</div>
                  <div>{r.type} · {r.host}</div>
                  <div className="select-all break-all text-brand-700">{r.value}</div>
                </div>
              ))}
            </div>
          </details>

          <Table headers={['Mailbox', 'Status', 'Warm-up-dag', 'Dagcap', 'Max cap', 'Vandaag']}>
            {d.mailboxes.map((mb) => (
              <tr key={mb.id}>
                <td className="px-4 py-3 font-medium">{mb.email}</td>
                <td className="px-4 py-3"><Badge color={statusColor(mb.status)}>{mb.status}</Badge></td>
                <td className="px-4 py-3">{mb.warmupDay}</td>
                <td className="px-4 py-3">{mb.dailyCap}</td>
                <td className="px-4 py-3">
                  <form action={setMaxCap} className="flex items-center gap-2">
                    <input type="hidden" name="mailboxId" value={mb.id} />
                    <Input name="maxDailyCap" type="number" defaultValue={mb.maxDailyCap} style={{ width: 80 }} />
                    <Button type="submit" variant="secondary">Zet</Button>
                  </form>
                  {session?.role !== 'ADMIN' && <div className="mt-1 text-xs text-gray-400">&gt;50 alleen door ADMIN</div>}
                </td>
                <td className="px-4 py-3">{mb.sentToday}</td>
              </tr>
            ))}
          </Table>

          <details className="mt-4">
            <summary className="cursor-pointer text-sm font-medium text-brand-600">Mailbox toevoegen</summary>
            <form action={createMailbox} className="mt-3 grid grid-cols-3 gap-3">
              <input type="hidden" name="sendingDomainId" value={d.id} />
              <div><label className="mb-1 block text-xs">E-mail</label><Input name="email" type="email" required /></div>
              <div><label className="mb-1 block text-xs">Weergavenaam</label><Input name="displayName" required /></div>
              <div />
              <div><label className="mb-1 block text-xs">SMTP-host</label><Input name="smtpHost" required /></div>
              <div><label className="mb-1 block text-xs">SMTP-poort</label><Input name="smtpPort" type="number" defaultValue={587} /></div>
              <div><label className="mb-1 block text-xs">SMTP-gebruiker</label><Input name="smtpUser" required /></div>
              <div><label className="mb-1 block text-xs">SMTP-wachtwoord (app-password)</label><Input name="smtpPass" type="password" required /></div>
              <div><label className="mb-1 block text-xs">IMAP-host</label><Input name="imapHost" required /></div>
              <div><label className="mb-1 block text-xs">IMAP-poort</label><Input name="imapPort" type="number" defaultValue={993} /></div>
              <div><label className="mb-1 block text-xs">IMAP-gebruiker</label><Input name="imapUser" required /></div>
              <div><label className="mb-1 block text-xs">IMAP-wachtwoord</label><Input name="imapPass" type="password" required /></div>
              <div className="flex items-end"><Button type="submit">Toevoegen (start warm-up)</Button></div>
            </form>
            <p className="mt-2 text-xs text-gray-500">Wachtwoorden worden AES-256-GCM versleuteld opgeslagen. Nieuwe mailboxen starten altijd in warm-up: week 1: 10/dag → week 4: 50/dag.</p>
          </details>
        </Card>
      ))}

      <Card title="Nieuw verzenddomein">
        <form action={createDomain} className="grid max-w-xl grid-cols-3 items-end gap-3">
          <div>
            <label className="mb-1 block text-xs">Klant</label>
            <select name="tenantId" className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm">
              {tenants.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
            </select>
          </div>
          <div><label className="mb-1 block text-xs">Domein</label><Input name="domain" placeholder="mail.klant.nl" required /></div>
          <div><label className="mb-1 block text-xs">DKIM-selector</label><Input name="dkimSelector" defaultValue="default" /></div>
          <div className="col-span-3"><Button type="submit">Domein toevoegen &amp; checken</Button></div>
        </form>
      </Card>
    </div>
  );
}
