// AVG data-export per tenant (§15): CSV van alle contacten + activiteiten.
import { NextResponse } from 'next/server';
import { requireStaff } from '@/lib/auth';
import { tenantDb } from '@/lib/tenancy';

export async function GET(_req: Request, { params }: { params: { tenantId: string } }) {
  try {
    await requireStaff();
  } catch {
    return new NextResponse('Geen toegang', { status: 403 });
  }
  const db = tenantDb(params.tenantId);
  const contacts = await db.contact.findMany({ include: { company: true, activities: true } });
  const rows = [['voornaam', 'achternaam', 'email', 'functie', 'bedrijf', 'status', 'bron', 'activiteiten']];
  for (const c of contacts) {
    rows.push([
      c.firstName, c.lastName, c.email, c.title ?? '', c.company.name, c.emailStatus, c.source,
      c.activities.map((a) => `${a.occurredAt.toISOString()} ${a.type}`).join(' | '),
    ]);
  }
  const csv = rows.map((r) => r.map((v) => `"${String(v).replace(/"/g, '""')}"`).join(';')).join('\n');
  return new NextResponse(csv, {
    headers: {
      'Content-Type': 'text/csv; charset=utf-8',
      'Content-Disposition': `attachment; filename="export-${params.tenantId}.csv"`,
    },
  });
}
