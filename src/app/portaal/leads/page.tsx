import { requireClient } from '@/lib/auth';
import { tenantDb } from '@/lib/tenancy';
import { prisma } from '@/lib/db';
import { Card, Badge, statusColor } from '@/components/ui';

export const dynamic = 'force-dynamic';

const STATUS_NL: Record<string, string> = {
  NEW: 'Nieuw', QUALIFIED: 'Gekwalificeerd', MEETING_BOOKED: 'Afspraak gepland', REJECTED: 'Afgewezen',
};

export default async function LeadsPage() {
  const session = await requireClient();
  const db = tenantDb(session.tenantId);
  const leads = await db.lead.findMany({
    include: { contact: { include: { company: true } } },
    orderBy: { createdAt: 'desc' },
    take: 100,
  });
  const messages = await prisma.message.findMany({
    where: { tenantId: session.tenantId, enrollment: { contactId: { in: leads.map((l) => l.contactId) } } },
    orderBy: { createdAt: 'asc' },
    include: { enrollment: { select: { contactId: true } } },
  });
  const byContact = new Map<string, typeof messages>();
  for (const m of messages) {
    const cid = m.enrollment?.contactId;
    if (!cid) continue;
    const list = byContact.get(cid) ?? [];
    list.push(m);
    byContact.set(cid, list);
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold">Leads</h1>
      {leads.map((lead) => {
        const convo = byContact.get(lead.contactId) ?? [];
        return (
          <Card key={lead.id}>
            <div className="mb-2 flex items-center gap-2">
              <span className="font-semibold">{lead.contact.firstName} {lead.contact.lastName}</span>
              <span className="text-sm text-gray-500">· {lead.contact.company.name}</span>
              <Badge color={statusColor(lead.status)}>{STATUS_NL[lead.status] ?? lead.status}</Badge>
              {lead.viaReferral && <Badge color="blue">via doorverwijzing</Badge>}
              <span className="ml-auto text-xs text-gray-400">{lead.createdAt.toLocaleDateString('nl-NL')}</span>
            </div>
            <details>
              <summary className="cursor-pointer text-sm text-brand-600">Conversatie bekijken</summary>
              <div className="mt-3 space-y-2">
                {convo.map((m) => (
                  <div key={m.id} className={`rounded-lg p-3 text-sm ${m.direction === 'OUT' ? 'bg-gray-50' : 'bg-brand-50'}`}>
                    <div className="mb-1 text-xs text-gray-400">{m.direction === 'OUT' ? 'Verzonden' : 'Ontvangen'} · {m.subject}</div>
                    <pre className="whitespace-pre-wrap font-sans">{m.body}</pre>
                  </div>
                ))}
              </div>
            </details>
          </Card>
        );
      })}
      {leads.length === 0 && <p className="text-gray-500">Nog geen leads — zodra er een positieve reactie binnenkomt, verschijnt die hier direct.</p>}
    </div>
  );
}
