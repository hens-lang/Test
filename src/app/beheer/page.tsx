// Intern monitoring-dashboard (§7f): mailboxen, domeinen, queue-status, guardrails.
import { prisma } from '@/lib/db';
import { requireStaff } from '@/lib/auth';
import { Card, StatTile, Table, Badge, statusColor } from '@/components/ui';
import { getSendMode } from '@/lib/env';

export const dynamic = 'force-dynamic';

export default async function MonitoringPage() {
  await requireStaff();
  const [mailboxes, domains, pendingSends, leadsThisWeek, draftsProposed] = await Promise.all([
    prisma.mailbox.findMany({ include: { sendingDomain: true } }),
    prisma.sendingDomain.findMany({ include: { tenant: true } }),
    prisma.enrollment.count({ where: { status: 'ACTIVE', nextSendAt: { not: null } } }),
    prisma.lead.count({ where: { createdAt: { gte: new Date(Date.now() - 7 * 86400_000) } } }),
    prisma.replyDraft.count({ where: { status: 'PROPOSED' } }),
  ]);

  const editStats = await prisma.replyDraft.findMany({
    where: { status: 'SENT', generatedBy: 'AI', finalBody: { not: null } },
    select: { draftBody: true, finalBody: true },
    take: 100,
  });
  const editedCount = editStats.filter((d) => d.finalBody!.trim() !== d.draftBody.trim()).length;
  const editPct = editStats.length > 0 ? Math.round((editedCount / editStats.length) * 100) : null;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Monitoring</h1>
        <Badge color={getSendMode() === 'demo' ? 'orange' : 'green'}>
          Verzendmodus: {getSendMode().toUpperCase()}
        </Badge>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatTile label="Geplande verzendingen" value={pendingSends} />
        <StatTile label="Leads deze week" value={leadsThisWeek} />
        <StatTile label="Concepten te beoordelen" value={draftsProposed} />
        <StatTile
          label="AI-concepten bewerkt"
          value={editPct !== null ? `${editPct}%` : '—'}
          sub="van de laatste 100 verzonden concepten"
        />
      </div>

      <Card title="Mailboxen">
        <Table headers={['Mailbox', 'Status', 'Warm-up', 'Vandaag', 'Cap', 'Bounces vandaag', 'Laatste fout']}>
          {mailboxes.map((mb) => {
            const usage = mb.dailyCap > 0 ? mb.sentToday / mb.dailyCap : 0;
            return (
              <tr key={mb.id}>
                <td className="px-4 py-3 font-medium">{mb.email}</td>
                <td className="px-4 py-3"><Badge color={statusColor(mb.status)}>{mb.status}</Badge></td>
                <td className="px-4 py-3">{mb.status === 'WARMING' ? `dag ${mb.warmupDay}` : '✓ voltooid'}</td>
                <td className="px-4 py-3">
                  <Badge color={usage >= 1 ? 'red' : usage > 0.8 ? 'orange' : 'green'}>
                    {mb.sentToday}/{mb.dailyCap}
                  </Badge>
                </td>
                <td className="px-4 py-3">{mb.dailyCap}</td>
                <td className="px-4 py-3">{mb.bouncedToday}</td>
                <td className="px-4 py-3 text-xs text-gray-500">{mb.lastError?.slice(0, 60) ?? '—'}</td>
              </tr>
            );
          })}
        </Table>
      </Card>

      <Card title="Verzenddomeinen">
        <Table headers={['Domein', 'Klant', 'Status', 'SPF', 'DKIM', 'DMARC', 'MX', 'Health', 'Laatst gecheckt']}>
          {domains.map((d) => (
            <tr key={d.id}>
              <td className="px-4 py-3 font-medium">{d.domain}</td>
              <td className="px-4 py-3">{d.tenant.name}</td>
              <td className="px-4 py-3"><Badge color={statusColor(d.status)}>{d.status}</Badge></td>
              <td className="px-4 py-3">{d.spfOk ? '✓' : '✗'}</td>
              <td className="px-4 py-3">{d.dkimOk ? '✓' : '✗'}</td>
              <td className="px-4 py-3">{d.dmarcOk ? '✓' : '✗'}</td>
              <td className="px-4 py-3">{d.mxOk ? '✓' : '✗'}</td>
              <td className="px-4 py-3">
                <Badge color={d.healthScore >= 80 ? 'green' : d.healthScore >= 50 ? 'orange' : 'red'}>
                  {d.healthScore}
                </Badge>
              </td>
              <td className="px-4 py-3 text-xs text-gray-500">
                {d.lastCheckedAt ? d.lastCheckedAt.toLocaleString('nl-NL') : 'nooit'}
              </td>
            </tr>
          ))}
        </Table>
      </Card>
    </div>
  );
}
