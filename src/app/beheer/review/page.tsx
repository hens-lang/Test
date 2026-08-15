// Reviewflow (§6): per prospect de opener zien, aanpassen, goedkeuren of afkeuren.
// Bulk-goedkeuren kan, maar de gerenderde eerste mail wordt altijd getoond.
import { prisma } from '@/lib/db';
import { requireStaff } from '@/lib/auth';
import { Card, Button, Textarea, Badge } from '@/components/ui';
import { renderTemplate, buildVars } from '@/core/template';
import { approveOpener, rejectOpener, bulkApprove } from '../actions';

export const dynamic = 'force-dynamic';

export default async function ReviewPage() {
  await requireStaff();
  const pending = await prisma.enrollment.findMany({
    where: { status: 'PENDING_APPROVAL' },
    include: {
      contact: { include: { company: true } },
      campaign: { include: { tenant: true, sequenceSteps: { orderBy: { order: 'asc' }, take: 1 } } },
    },
    orderBy: { createdAt: 'asc' },
    take: 50,
  });
  const generating = await prisma.enrollment.count({ where: { status: 'PENDING_PERSONALIZATION' } });
  const byCampaign = new Map<string, typeof pending>();
  for (const e of pending) {
    const list = byCampaign.get(e.campaignId) ?? [];
    list.push(e);
    byCampaign.set(e.campaignId, list);
  }

  return (
    <div className="max-w-3xl space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Review openers</h1>
        <div className="text-sm text-gray-500">
          {pending.length} te beoordelen{generating > 0 && ` · ${generating} in generatie`}
        </div>
      </div>

      {pending.length === 0 && <p className="text-gray-500">Niets te beoordelen. 🎉</p>}

      {[...byCampaign.entries()].map(([campaignId, enrollments]) => (
        <div key={campaignId} className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold">{enrollments[0].campaign.name} <span className="text-sm text-gray-400">({enrollments[0].campaign.tenant.name})</span></h2>
            <form action={bulkApprove}>
              <input type="hidden" name="campaignId" value={campaignId} />
              <Button type="submit" variant="secondary">Alles goedkeuren ({enrollments.length})</Button>
            </form>
          </div>
          {enrollments.map((e) => {
            const step = e.campaign.sequenceSteps[0];
            const vars = buildVars({
              firstName: e.contact.firstName,
              lastName: e.contact.lastName,
              companyName: e.contact.company.name,
              title: e.contact.title,
              city: e.contact.company.city,
              opener: e.personalizedOpener,
              customFields: (e.contact.customFields as Record<string, unknown>) ?? {},
            });
            const rendered = step ? renderTemplate(step.bodyA, vars) : null;
            return (
              <Card key={e.id}>
                <div className="mb-2 flex items-center gap-2 text-sm">
                  <span className="font-medium">{e.contact.firstName} {e.contact.lastName}</span>
                  <span className="text-gray-400">· {e.contact.company.name}</span>
                  {e.contact.company.industry && <Badge color="blue">{e.contact.company.industry}</Badge>}
                </div>
                <form action={approveOpener} className="space-y-3">
                  <input type="hidden" name="enrollmentId" value={e.id} />
                  <div>
                    <label className="mb-1 block text-xs text-gray-500">Opener (aanpasbaar)</label>
                    <Textarea name="opener" rows={2} defaultValue={e.personalizedOpener ?? ''} />
                  </div>
                  {rendered && (
                    <details>
                      <summary className="cursor-pointer text-xs text-gray-500">Gerenderde eerste mail tonen</summary>
                      <pre className="mt-2 whitespace-pre-wrap rounded-lg bg-gray-50 p-3 font-sans text-sm">{rendered.text}</pre>
                    </details>
                  )}
                  <div className="flex gap-2">
                    <Button type="submit">Goedkeuren</Button>
                    <Button type="submit" formAction={rejectOpener} variant="secondary">Afkeuren &amp; regenereren</Button>
                  </div>
                </form>
              </Card>
            );
          })}
        </div>
      ))}
    </div>
  );
}
