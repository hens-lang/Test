// Referral-werklijst (§9): voorgestelde doorverwijzingen beoordelen en opvolgen.
import { prisma } from '@/lib/db';
import { requireStaff } from '@/lib/auth';
import { Card, Button, Input, Badge, StatTile, statusColor } from '@/components/ui';
import { updateReferral, approveReferral, rejectReferral } from '../actions';

export const dynamic = 'force-dynamic';

export default async function ReferralsPage({ searchParams }: { searchParams: { error?: string } }) {
  await requireStaff();
  const referrals = await prisma.referral.findMany({
    where: { status: { in: ['SUGGESTED', 'APPROVED'] } },
    include: { tenant: true },
    orderBy: { createdAt: 'desc' },
    take: 50,
  });
  const sourceContacts = await prisma.contact.findMany({
    where: { id: { in: referrals.map((r) => r.sourceContactId) } },
    include: { company: true },
  });
  const sourceById = new Map(sourceContacts.map((c) => [c.id, c]));
  const [received, followedUp, converted] = await Promise.all([
    prisma.referral.count(),
    prisma.referral.count({ where: { status: 'CONTACT_CREATED' } }),
    prisma.lead.count({ where: { viaReferral: true } }),
  ]);

  const ERR: Record<string, string> = {
    'geen-adres': 'Geen e-mailadres bekend — vul eerst handmatig een adres in (nooit raden).',
    gesupprimeerd: 'Dit adres staat op de suppressielijst en mag niet benaderd worden.',
    'geen-mailboxen': 'Geen actieve mailbox beschikbaar voor deze klant.',
  };

  return (
    <div className="max-w-3xl space-y-6">
      <h1 className="text-xl font-bold">Referral-werklijst</h1>
      {searchParams.error && <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{ERR[searchParams.error] ?? searchParams.error}</div>}

      <div className="grid grid-cols-3 gap-4">
        <StatTile label="Referrals ontvangen" value={received} />
        <StatTile label="Opgevolgd" value={followedUp} />
        <StatTile label="Geconverteerd naar lead" value={converted} />
      </div>

      {referrals.map((r) => {
        const source = sourceById.get(r.sourceContactId);
        return (
          <Card key={r.id}>
            <div className="mb-2 flex items-center gap-2 text-sm">
              <Badge color={statusColor(r.status)}>{r.status}</Badge>
              <span className="text-gray-500">
                Verwezen door {source ? `${source.firstName} ${source.lastName} (${source.company.name})` : 'onbekend'} · {r.tenant.name}
              </span>
            </div>
            <blockquote className="mb-4 rounded-lg border-l-4 border-brand-500 bg-gray-50 p-3 text-sm italic">
              &ldquo;{r.rawSnippet}&rdquo;
            </blockquote>
            <form action={approveReferral} className="space-y-3">
              <input type="hidden" name="id" value={r.id} />
              <div className="grid grid-cols-4 gap-3">
                <div><label className="mb-1 block text-xs">Naam</label><Input name="suggestedName" defaultValue={r.suggestedName ?? ''} /></div>
                <div>
                  <label className="mb-1 block text-xs">E-mail {!r.suggestedEmail && <span className="text-orange-600">(adres opzoeken!)</span>}</label>
                  <Input name="suggestedEmail" defaultValue={r.suggestedEmail ?? ''} placeholder="handmatig opzoeken" />
                </div>
                <div><label className="mb-1 block text-xs">Functie</label><Input name="suggestedTitle" defaultValue={r.suggestedTitle ?? ''} /></div>
                <div><label className="mb-1 block text-xs">Bedrijf</label><Input name="suggestedCompany" defaultValue={r.suggestedCompany ?? ''} /></div>
              </div>
              <div className="flex gap-2">
                <Button type="submit" formAction={updateReferral} variant="secondary">Gegevens opslaan</Button>
                <Button type="submit">Maak contact + start opvolging</Button>
                <Button type="submit" formAction={rejectReferral} variant="danger">Afwijzen</Button>
              </div>
              <p className="text-xs text-gray-400">
                Opvolging: nieuw contact (source=REFERRAL), suppressie-check en validatie, en een concept-referralmail met {'{{verwijzer_naam}}'} in de reviewflow.
              </p>
            </form>
          </Card>
        );
      })}
      {referrals.length === 0 && <p className="text-gray-500">Geen openstaande referral-suggesties.</p>}
    </div>
  );
}
