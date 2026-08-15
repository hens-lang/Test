// Campagnedetail: sequence-editor, content-lint-checklist, preview op echte
// prospects, template-suggesties uit de bibliotheek en activatie.
import { prisma } from '@/lib/db';
import { requireStaff } from '@/lib/auth';
import { notFound } from 'next/navigation';
import { Card, Badge, Button, Input, Textarea, statusColor } from '@/components/ui';
import { lintSequence, hasBlockers } from '@/core/lint';
import { renderTemplate, buildVars } from '@/core/template';
import { isDisplayable } from '@/core/anonymize';
import { saveStep, deleteStep, enrollProspects, activateCampaign, pauseCampaign, sendNow } from '../../actions';

export const dynamic = 'force-dynamic';

const ERRORS: Record<string, string> = {
  lint: 'Activatie geblokkeerd: los eerst de blockers in de spam-check op.',
  'geen-stappen': 'Activatie geblokkeerd: voeg minstens één stap toe.',
  variabelen: 'Activatie geblokkeerd: variabelen resolven voor minder dan 95% van de selectie.',
  emailstatus: 'Activatie geblokkeerd: doelgroep bevat contacten met een niet-toegestane e-mailstatus.',
  'geen-mailboxen': 'Er zijn geen actieve mailboxen voor deze klant.',
};

export default async function CampaignDetail({ params, searchParams }: { params: { id: string }; searchParams: { error?: string } }) {
  await requireStaff();
  const campaign = await prisma.campaign.findUnique({
    where: { id: params.id },
    include: {
      tenant: true,
      sequenceSteps: { orderBy: { order: 'asc' } },
      enrollments: {
        include: { contact: { include: { company: true } } },
        take: 500,
      },
    },
  });
  if (!campaign) notFound();

  const issues = lintSequence(campaign.sequenceSteps);
  const statusCounts = campaign.enrollments.reduce<Record<string, number>>((acc, e) => {
    acc[e.status] = (acc[e.status] ?? 0) + 1;
    return acc;
  }, {});

  // Preview: 5 willekeurige echte prospects uit de selectie (§5).
  const sampled = [...campaign.enrollments].sort(() => 0.5 - Math.random()).slice(0, 5);
  const firstStep = campaign.sequenceSteps[0];
  const previews = firstStep
    ? sampled.map((e) => {
        const vars = buildVars({
          firstName: e.contact.firstName,
          lastName: e.contact.lastName,
          companyName: e.contact.company.name,
          title: e.contact.title,
          city: e.contact.company.city,
          opener: e.personalizedOpener ?? '(opener nog niet gegenereerd)',
          customFields: (e.contact.customFields as Record<string, unknown>) ?? {},
        });
        return {
          name: `${e.contact.firstName} ${e.contact.lastName}`,
          subject: renderTemplate(firstStep.subjectA, vars),
          body: renderTemplate(firstStep.bodyA, vars),
        };
      })
    : [];

  // Template-suggesties (§5/§12): best presterend in de branche van de tenant.
  const industry = campaign.tenant.industry || 'algemeen';
  const suggestions = (
    await prisma.templateStat.findMany({
      where: { industry, kind: { in: ['SUBJECT', 'OPENER'] } },
      orderBy: { replyCount: 'desc' },
      take: 10,
    })
  ).filter((s) => isDisplayable(s.sentCount)).slice(0, 5);

  const dueEnrollments = campaign.enrollments.filter((e) => e.status === 'ACTIVE').slice(0, 10);

  return (
    <div className="max-w-4xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">{campaign.name}</h1>
          <p className="text-sm text-gray-500">{campaign.tenant.name} · venster {campaign.sendWindowStart}–{campaign.sendWindowEnd}</p>
        </div>
        <div className="flex items-center gap-3">
          <Badge color={statusColor(campaign.status)}>{campaign.status}</Badge>
          {campaign.status !== 'ACTIVE' ? (
            <form action={activateCampaign}>
              <input type="hidden" name="campaignId" value={campaign.id} />
              <Button type="submit">Activeren</Button>
            </form>
          ) : (
            <form action={pauseCampaign}>
              <input type="hidden" name="campaignId" value={campaign.id} />
              <Button type="submit" variant="secondary">Pauzeren</Button>
            </form>
          )}
        </div>
      </div>

      {searchParams.error && <div className="rounded-lg bg-red-50 p-4 text-sm text-red-700">{ERRORS[searchParams.error] ?? searchParams.error}</div>}

      <div className="flex flex-wrap gap-2">
        {Object.entries(statusCounts).map(([s, n]) => (
          <Badge key={s} color={statusColor(s)}>{s}: {n}</Badge>
        ))}
      </div>

      <Card title="Spam-check (content-lint)">
        {issues.length === 0 ? (
          <p className="text-sm text-green-700">✓ Geen problemen gevonden.</p>
        ) : (
          <ul className="space-y-1 text-sm">
            {issues.map((i, idx) => (
              <li key={idx} className={i.level === 'blocker' ? 'text-red-700' : 'text-orange-600'}>
                {i.level === 'blocker' ? '✗ BLOCKER' : '⚠'} {i.message}
              </li>
            ))}
          </ul>
        )}
        {hasBlockers(issues) && <p className="mt-2 text-xs text-gray-500">Blockers moeten opgelost zijn vóór activatie.</p>}
      </Card>

      {suggestions.length > 0 && (
        <Card title={`Best presterend in "${industry}"`}>
          <ul className="space-y-2 text-sm">
            {suggestions.map((s) => (
              <li key={s.id} className="flex items-center justify-between gap-4">
                <span className="font-mono text-xs">{s.textSample.slice(0, 80)}</span>
                <Badge color="green">{((s.replyCount / Math.max(1, s.sentCount)) * 100).toFixed(1)}% reply</Badge>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {campaign.sequenceSteps.map((step, i) => (
        <Card key={step.id} title={`Stap ${i + 1} (na ${step.waitDays} dagen)`}>
          <form action={saveStep} className="space-y-3">
            <input type="hidden" name="campaignId" value={campaign.id} />
            <input type="hidden" name="stepId" value={step.id} />
            <div className="grid grid-cols-4 gap-3">
              <div><label className="mb-1 block text-xs">Wachtdagen</label><Input name="waitDays" type="number" defaultValue={step.waitDays} /></div>
              <div className="col-span-3"><label className="mb-1 block text-xs">Onderwerp A</label><Input name="subjectA" defaultValue={step.subjectA} /></div>
            </div>
            <div><label className="mb-1 block text-xs">Body A</label><Textarea name="bodyA" rows={6} defaultValue={step.bodyA} /></div>
            <details>
              <summary className="cursor-pointer text-sm text-gray-500">B-variant (A/B-test, split {step.abSplit}%)</summary>
              <div className="mt-3 space-y-3">
                <div><label className="mb-1 block text-xs">Onderwerp B</label><Input name="subjectB" defaultValue={step.subjectB ?? ''} /></div>
                <div><label className="mb-1 block text-xs">Body B</label><Textarea name="bodyB" rows={6} defaultValue={step.bodyB ?? ''} /></div>
                <div><label className="mb-1 block text-xs">Split % naar A</label><Input name="abSplit" type="number" defaultValue={step.abSplit} /></div>
              </div>
            </details>
            <div className="flex gap-2">
              <Button type="submit" variant="secondary">Stap opslaan</Button>
              <Button type="submit" formAction={deleteStep} name="stepId" value={step.id} variant="danger">Verwijderen</Button>
            </div>
          </form>
        </Card>
      ))}

      <Card title="Nieuwe stap">
        <form action={saveStep} className="space-y-3">
          <input type="hidden" name="campaignId" value={campaign.id} />
          <div className="grid grid-cols-4 gap-3">
            <div><label className="mb-1 block text-xs">Wachtdagen</label><Input name="waitDays" type="number" defaultValue={0} /></div>
            <div className="col-span-3"><label className="mb-1 block text-xs">Onderwerp</label><Input name="subjectA" placeholder="Gebruik {{voornaam}}, {{bedrijf}}, {{opener}}…" /></div>
          </div>
          <div><label className="mb-1 block text-xs">Body</label><Textarea name="bodyA" rows={6} placeholder={'Beste {{voornaam}},\n\n{{opener}}\n\n…'} /></div>
          <Button type="submit" variant="secondary">Stap toevoegen</Button>
        </form>
      </Card>

      <Card title="Doelgroep enrollen">
        <form action={enrollProspects} className="flex items-center gap-4">
          <input type="hidden" name="campaignId" value={campaign.id} />
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" name="allowRisky" value="1" /> Ook RISKY-adressen toestaan (expliciete keuze)
          </label>
          <Button type="submit" variant="secondary">Alle geschikte prospects enrollen</Button>
        </form>
        <p className="mt-2 text-xs text-gray-500">
          Alleen VALID (en optioneel RISKY) adressen; suppressielijst wordt gecheckt; mailboxen worden round-robin toegewezen; personalisatie start direct.
        </p>
      </Card>

      {previews.length > 0 && (
        <Card title="Preview (5 willekeurige echte prospects)">
          <div className="space-y-4">
            {previews.map((p, i) => (
              <div key={i} className="rounded-lg border border-gray-100 bg-gray-50 p-4 text-sm">
                <div className="mb-1 text-xs text-gray-500">{p.name}</div>
                <div className="font-semibold">{p.subject.text} {!p.subject.ok && <Badge color="red">variabelen missen</Badge>}</div>
                <pre className="mt-2 whitespace-pre-wrap font-sans">{p.body.text}</pre>
              </div>
            ))}
          </div>
        </Card>
      )}

      {dueEnrollments.length > 0 && (
        <Card title="Demo: verzending direct uitvoeren">
          <div className="space-y-2">
            {dueEnrollments.map((e) => (
              <form key={e.id} action={sendNow} className="flex items-center gap-3 text-sm">
                <input type="hidden" name="enrollmentId" value={e.id} />
                <span>{e.contact.firstName} {e.contact.lastName} (stap {e.currentStep + 1})</span>
                <Button type="submit" variant="secondary">Nu &quot;versturen&quot;</Button>
              </form>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
