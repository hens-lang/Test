import { requireClient } from '@/lib/auth';
import { tenantDb } from '@/lib/tenancy';
import { Table, Badge, statusColor } from '@/components/ui';

export const dynamic = 'force-dynamic';

const ENROLLMENT_NL: Record<string, string> = {
  PENDING_PERSONALIZATION: 'Wordt voorbereid', PENDING_APPROVAL: 'In review', ACTIVE: 'In campagne',
  REPLIED: 'Heeft gereageerd', BOUNCED: 'Niet bezorgbaar', UNSUBSCRIBED: 'Afgemeld',
  COMPLETED: 'Sequence afgerond', STOPPED: 'Gestopt',
};

export default async function ProspectsPortaal() {
  const session = await requireClient();
  const db = tenantDb(session.tenantId);
  const contacts = await db.contact.findMany({
    include: {
      company: true,
      enrollments: { orderBy: { createdAt: 'desc' }, take: 1, include: { campaign: true } },
      activities: { orderBy: { occurredAt: 'desc' }, take: 1 },
    },
    orderBy: { updatedAt: 'desc' },
    take: 200,
  });

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold">Prospects</h1>
      <p className="text-sm text-gray-500">Live status van alle benaderde prospects (alleen-lezen).</p>
      <Table headers={['Naam', 'Bedrijf', 'Status', 'Stap', 'Laatste activiteit']}>
        {contacts.map((c) => {
          const e = c.enrollments[0];
          return (
            <tr key={c.id}>
              <td className="px-4 py-3 font-medium">{c.firstName} {c.lastName}<div className="text-xs text-gray-400">{c.title}</div></td>
              <td className="px-4 py-3">{c.company.name}</td>
              <td className="px-4 py-3">
                {e ? <Badge color={statusColor(e.status)}>{ENROLLMENT_NL[e.status] ?? e.status}</Badge> : <Badge>Nog niet benaderd</Badge>}
              </td>
              <td className="px-4 py-3 text-sm">{e ? `${e.currentStep + 1} (${e.campaign.name})` : '—'}</td>
              <td className="px-4 py-3 text-xs text-gray-500">{c.activities[0]?.occurredAt.toLocaleString('nl-NL') ?? '—'}</td>
            </tr>
          );
        })}
      </Table>
    </div>
  );
}
