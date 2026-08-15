import { prisma } from '@/lib/db';
import { requireStaff } from '@/lib/auth';
import { notFound } from 'next/navigation';
import { Card, Badge, statusColor } from '@/components/ui';

export const dynamic = 'force-dynamic';

const TYPE_LABELS: Record<string, string> = {
  EMAIL_QUEUED: 'Ingepland', EMAIL_SENT: 'Mail verzonden', EMAIL_OPENED: 'Geopend',
  EMAIL_CLICKED: 'Geklikt', EMAIL_REPLIED: 'Reactie ontvangen', EMAIL_BOUNCED: 'Bounce',
  EMAIL_UNSUBSCRIBED: 'Afgemeld', LEAD_CREATED: 'Lead aangemaakt', REFERRAL_RECEIVED: 'Doorverwijzing ontvangen',
  NOTE: 'Notitie', CALL_MADE: 'Gebeld', CALL_RESULT: 'Belresultaat',
};

export default async function ContactDetail({ params }: { params: { id: string } }) {
  await requireStaff();
  const contact = await prisma.contact.findUnique({
    where: { id: params.id },
    include: {
      company: true,
      activities: { orderBy: { occurredAt: 'desc' }, take: 50 },
      enrollments: { include: { campaign: true } },
    },
  });
  if (!contact) notFound();

  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <h1 className="text-xl font-bold">{contact.firstName} {contact.lastName}</h1>
        <p className="text-sm text-gray-500">{contact.title} · {contact.company.name} · {contact.email}</p>
        <div className="mt-2 flex gap-2">
          <Badge color={statusColor(contact.emailStatus)}>{contact.emailStatus}</Badge>
          <Badge color="blue">{contact.source}</Badge>
        </div>
      </div>

      <Card title="Campagnes">
        <ul className="space-y-2 text-sm">
          {contact.enrollments.map((e) => (
            <li key={e.id} className="flex items-center gap-3">
              <span className="font-medium">{e.campaign.name}</span>
              <Badge color={statusColor(e.status)}>{e.status}</Badge>
              <span className="text-xs text-gray-500">stap {e.currentStep + 1}</span>
            </li>
          ))}
          {contact.enrollments.length === 0 && <li className="text-gray-500">Niet in een campagne.</li>}
        </ul>
      </Card>

      <Card title="Activity-tijdlijn">
        <ol className="space-y-3">
          {contact.activities.map((a) => (
            <li key={a.id} className="flex items-start gap-3 text-sm">
              <span className="w-36 shrink-0 text-xs text-gray-400">{a.occurredAt.toLocaleString('nl-NL')}</span>
              <span>{TYPE_LABELS[a.type] ?? a.type}</span>
            </li>
          ))}
        </ol>
      </Card>
    </div>
  );
}
