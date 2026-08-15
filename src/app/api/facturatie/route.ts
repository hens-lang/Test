// Maandelijks facturatie-overzicht als CSV (§13) — input voor de boekhouding.
import { NextResponse } from 'next/server';
import { prisma } from '@/lib/db';
import { requireStaff } from '@/lib/auth';

export async function GET() {
  try {
    await requireStaff();
  } catch {
    return new NextResponse('Geen toegang', { status: 403 });
  }
  const monthStart = new Date();
  monthStart.setUTCDate(1);
  monthStart.setUTCHours(0, 0, 0, 0);

  const subs = await prisma.subscription.findMany({
    where: { status: { in: ['ACTIVE', 'TRIAL'] } },
    include: { tenant: true, plan: true },
  });
  const rows = [['tenant', 'plan', 'type', 'status', 'prijs_eur', 'leads_deze_maand', 'contacten']];
  for (const s of subs) {
    const [leads, contacts] = await Promise.all([
      prisma.lead.count({ where: { tenantId: s.tenantId, createdAt: { gte: monthStart } } }),
      prisma.contact.count({ where: { tenantId: s.tenantId } }),
    ]);
    rows.push([
      s.tenant.name,
      s.plan.name,
      s.plan.type,
      s.status,
      ((s.priceOverrideCents ?? s.plan.monthlyPriceCents) / 100).toFixed(2),
      String(leads),
      String(contacts),
    ]);
  }
  const csv = rows.map((r) => r.map((c) => `"${c.replace(/"/g, '""')}"`).join(';')).join('\n');
  return new NextResponse(csv, {
    headers: {
      'Content-Type': 'text/csv; charset=utf-8',
      'Content-Disposition': `attachment; filename="facturatie-${monthStart.toISOString().slice(0, 7)}.csv"`,
    },
  });
}
