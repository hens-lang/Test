import Link from 'next/link';
import { prisma } from '@/lib/db';
import { tenantDb } from '@/lib/tenancy';
import { requireStaff } from '@/lib/auth';
import { Table, Badge, Button, statusColor } from '@/components/ui';
import { validateNow } from '../actions';

export const dynamic = 'force-dynamic';

export default async function ProspectsPage({ searchParams }: { searchParams: { tenantId?: string; status?: string } }) {
  await requireStaff();
  const tenants = await prisma.tenant.findMany({ orderBy: { name: 'asc' } });
  const tenantId = searchParams.tenantId || tenants[0]?.id;
  if (!tenantId) return <p>Maak eerst een klant aan.</p>;
  const db = tenantDb(tenantId);
  const contacts = await db.contact.findMany({
    where: searchParams.status ? { emailStatus: searchParams.status as never } : {},
    include: { company: true, enrollments: { include: { campaign: true }, take: 1, orderBy: { createdAt: 'desc' } } },
    orderBy: { createdAt: 'desc' },
    take: 200,
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Prospects</h1>
        <div className="flex gap-2">
          <form action={validateNow}>
            <input type="hidden" name="tenantId" value={tenantId} />
            <Button variant="secondary" type="submit">Validatie draaien</Button>
          </form>
          <Link href={`/beheer/prospects/import?tenantId=${tenantId}`}>
            <Button type="button">Importeren (CSV)</Button>
          </Link>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 text-sm">
        {tenants.map((t) => (
          <Link key={t.id} href={`/beheer/prospects?tenantId=${t.id}`}
            className={`rounded-full px-3 py-1 ${t.id === tenantId ? 'bg-brand-600 text-white' : 'bg-white border border-gray-300'}`}>
            {t.name}
          </Link>
        ))}
        <span className="mx-2 text-gray-300">|</span>
        {['VALID', 'RISKY', 'INVALID', 'UNVERIFIED', 'BOUNCED', 'UNSUBSCRIBED'].map((s) => (
          <Link key={s} href={`/beheer/prospects?tenantId=${tenantId}&status=${s}`}
            className={`rounded-full px-3 py-1 ${searchParams.status === s ? 'bg-gray-800 text-white' : 'bg-white border border-gray-300'}`}>
            {s}
          </Link>
        ))}
      </div>

      <Table headers={['Naam', 'Bedrijf', 'E-mailstatus', 'Bron', 'Campagne', '']}>
        {contacts.map((c) => (
          <tr key={c.id}>
            <td className="px-4 py-3 font-medium">{c.firstName} {c.lastName}<div className="text-xs text-gray-500">{c.title}</div></td>
            <td className="px-4 py-3">{c.company.name}<div className="text-xs text-gray-500">{c.company.city}</div></td>
            <td className="px-4 py-3"><Badge color={statusColor(c.emailStatus)}>{c.emailStatus}</Badge></td>
            <td className="px-4 py-3 text-xs">{c.source}</td>
            <td className="px-4 py-3 text-xs">{c.enrollments[0]?.campaign.name ?? '—'}</td>
            <td className="px-4 py-3"><Link className="text-brand-600 hover:underline" href={`/beheer/prospects/${c.id}`}>Detail →</Link></td>
          </tr>
        ))}
      </Table>
    </div>
  );
}
