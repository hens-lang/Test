// Reply-inbox (§8/§10): alle replies over alle tenants, met conversatie,
// classificatie-bevestiging, acties en het AI-conceptantwoord ernaast.
import { prisma } from '@/lib/db';
import { requireStaff } from '@/lib/auth';
import { Card, Button, Textarea, Badge, statusColor } from '@/components/ui';
import { makeLead, reclassify, stopEnrollment, unsubscribeContact, sendReply, discardDraft, simulateReply } from '../actions';

export const dynamic = 'force-dynamic';

const CLASSIFICATIONS = ['POSITIVE', 'REFERRAL', 'NOT_NOW', 'NEGATIVE', 'OOO', 'UNSUBSCRIBE', 'OTHER'];

export default async function InboxPage({ searchParams }: { searchParams: { klasse?: string; error?: string } }) {
  await requireStaff();
  const messages = await prisma.message.findMany({
    where: {
      direction: 'IN',
      ...(searchParams.klasse ? { classifiedAs: searchParams.klasse as never } : {}),
    },
    include: {
      tenant: true,
      enrollment: { include: { contact: { include: { company: true } }, campaign: true } },
      replyDrafts: { where: { status: { in: ['PROPOSED', 'EDITED'] } }, take: 1 },
    },
    orderBy: { createdAt: 'desc' },
    take: 50,
  });
  const activeEnrollments = await prisma.enrollment.findMany({
    where: { status: { in: ['ACTIVE', 'COMPLETED'] }, messages: { some: { direction: 'OUT' } } },
    include: { contact: true, campaign: true },
    take: 10,
    orderBy: { createdAt: 'desc' },
  });

  return (
    <div className="max-w-4xl space-y-6">
      <h1 className="text-xl font-bold">Reply-inbox</h1>
      {searchParams.error && <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{searchParams.error}</div>}

      <div className="flex flex-wrap gap-2 text-sm">
        <a href="/beheer/inbox" className={`rounded-full px-3 py-1 ${!searchParams.klasse ? 'bg-gray-800 text-white' : 'border border-gray-300 bg-white'}`}>Alles</a>
        {CLASSIFICATIONS.map((c) => (
          <a key={c} href={`/beheer/inbox?klasse=${c}`}
            className={`rounded-full px-3 py-1 ${searchParams.klasse === c ? 'bg-gray-800 text-white' : 'border border-gray-300 bg-white'}`}>
            {c}
          </a>
        ))}
      </div>

      {messages.map((m) => {
        const draft = m.replyDrafts[0];
        return (
          <Card key={m.id}>
            <div className="mb-3 flex flex-wrap items-center gap-2 text-sm">
              <span className="font-medium">{m.enrollment?.contact.firstName} {m.enrollment?.contact.lastName}</span>
              <span className="text-gray-400">· {m.enrollment?.contact.company.name} · {m.tenant.name}</span>
              {m.classifiedAs && (
                <Badge color={statusColor(m.classifiedAs === 'POSITIVE' ? 'ACTIVE' : m.classifiedAs)}>
                  {m.classifiedAs}{m.classificationConfirmed ? ' ✓' : ' (voorstel)'}
                </Badge>
              )}
              <span className="ml-auto text-xs text-gray-400">{m.receivedAt?.toLocaleString('nl-NL')}</span>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <div className="mb-1 text-xs font-semibold uppercase text-gray-400">Reply van prospect</div>
                <div className="rounded-lg bg-gray-50 p-3 text-sm">
                  <div className="mb-1 font-medium">{m.subject}</div>
                  <pre className="whitespace-pre-wrap font-sans">{m.body}</pre>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  <form action={makeLead}><input type="hidden" name="messageId" value={m.id} /><Button type="submit" variant="secondary">Maak lead</Button></form>
                  {m.enrollmentId && (
                    <form action={stopEnrollment}><input type="hidden" name="enrollmentId" value={m.enrollmentId} /><Button type="submit" variant="secondary">Stop enrollment</Button></form>
                  )}
                  <form action={unsubscribeContact}><input type="hidden" name="messageId" value={m.id} /><Button type="submit" variant="secondary">Unsubscribe</Button></form>
                  <form action={reclassify} className="flex items-center gap-1">
                    <input type="hidden" name="messageId" value={m.id} />
                    <select name="classification" defaultValue={m.classifiedAs ?? 'OTHER'} className="rounded-lg border border-gray-300 px-2 py-1.5 text-sm">
                      {CLASSIFICATIONS.map((c) => <option key={c}>{c}</option>)}
                    </select>
                    <Button type="submit" variant="secondary">Herclassificeer</Button>
                  </form>
                </div>
              </div>

              <div>
                <div className="mb-1 text-xs font-semibold uppercase text-gray-400">
                  Conceptantwoord {draft ? `(${draft.generatedBy === 'AI' ? 'AI' : 'template'})` : ''}
                </div>
                {draft ? (
                  <form action={sendReply} className="space-y-2">
                    <input type="hidden" name="draftId" value={draft.id} />
                    <Textarea name="finalBody" rows={8} defaultValue={draft.draftBody} />
                    <div className="flex gap-2">
                      <Button type="submit">Versturen als reply</Button>
                      <Button type="submit" formAction={discardDraft} variant="secondary">Weggooien</Button>
                    </div>
                    <p className="text-xs text-gray-400">Wordt verstuurd via dezelfde mailbox als de thread, met correcte In-Reply-To-headers. Nooit automatisch.</p>
                  </form>
                ) : (
                  <p className="text-sm text-gray-400">Geen concept (bounce/unsubscribe/OOO of al afgehandeld).</p>
                )}
              </div>
            </div>
          </Card>
        );
      })}
      {messages.length === 0 && <p className="text-gray-500">Geen replies gevonden.</p>}

      <Card title="Demo: reply simuleren">
        <div className="space-y-3">
          {activeEnrollments.map((e) => (
            <form key={e.id} action={simulateReply} className="flex items-end gap-3">
              <input type="hidden" name="enrollmentId" value={e.id} />
              <div className="flex-1">
                <label className="mb-1 block text-xs text-gray-500">
                  Reply van {e.contact.firstName} {e.contact.lastName} ({e.campaign.name})
                </label>
                <Textarea name="body" rows={2} placeholder="Bijv.: Interessant! Bel me morgen. — of: Daarvoor moet je bij collega Piet de Vries zijn, piet@bedrijf.nl" />
              </div>
              <Button type="submit" variant="secondary">Simuleer</Button>
            </form>
          ))}
          {activeEnrollments.length === 0 && <p className="text-sm text-gray-400">Nog geen enrollments met verzonden mail.</p>}
        </div>
      </Card>
    </div>
  );
}
