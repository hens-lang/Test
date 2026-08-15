// Suppressielijst-logica (§4/§7d): tenant-specifiek én globaal.
// Gesupprimeerde adressen worden nooit enrolled en nooit gemaild.
import { prisma } from '@/lib/db';
import type { SuppressionReason } from '@prisma/client';

/** Puur: bepaalt of een adres gesupprimeerd is gegeven de gevonden entries. */
export function isSuppressedByEntries(
  email: string,
  entries: { email: string; tenantId: string | null }[],
  tenantId: string,
): boolean {
  const e = email.trim().toLowerCase();
  return entries.some((s) => s.email === e && (s.tenantId === null || s.tenantId === tenantId));
}

export async function isSuppressed(tenantId: string, email: string): Promise<boolean> {
  const e = email.trim().toLowerCase();
  const hit = await prisma.suppression.findFirst({
    where: { email: e, OR: [{ tenantId: null }, { tenantId }] },
    select: { id: true },
  });
  return hit !== null;
}

/** Bulk-variant voor imports: geeft de subset terug die gesupprimeerd is. */
export async function findSuppressed(tenantId: string, emails: string[]): Promise<Set<string>> {
  const lowered = emails.map((e) => e.trim().toLowerCase());
  const hits = await prisma.suppression.findMany({
    where: { email: { in: lowered }, OR: [{ tenantId: null }, { tenantId }] },
    select: { email: true },
  });
  return new Set(hits.map((h) => h.email));
}

/**
 * Voegt toe aan de suppressielijst (global bij hard bounce/klacht, tenant bij unsubscribe)
 * en stopt alle actieve enrollments van dat adres binnen de tenant.
 */
export async function suppress(
  tenantId: string | null,
  email: string,
  reason: SuppressionReason,
): Promise<void> {
  const e = email.trim().toLowerCase();
  // Compound unique met nullable tenantId werkt niet via upsert; find-then-create.
  const existing = await prisma.suppression.findFirst({ where: { tenantId, email: e } });
  if (!existing) {
    await prisma.suppression.create({ data: { tenantId, email: e, reason } });
  }

  const contacts = await prisma.contact.findMany({
    where: tenantId ? { tenantId, email: e } : { email: e },
    select: { id: true, tenantId: true },
  });
  for (const c of contacts) {
    const newStatus = reason === 'UNSUBSCRIBE' ? 'UNSUBSCRIBED' : reason === 'HARD_BOUNCE' ? 'BOUNCED' : undefined;
    if (newStatus) {
      await prisma.contact.update({ where: { id: c.id }, data: { emailStatus: newStatus } });
    }
    await prisma.enrollment.updateMany({
      where: { contactId: c.id, status: { in: ['PENDING_PERSONALIZATION', 'PENDING_APPROVAL', 'ACTIVE'] } },
      data: {
        status: reason === 'UNSUBSCRIBE' ? 'UNSUBSCRIBED' : reason === 'HARD_BOUNCE' ? 'BOUNCED' : 'STOPPED',
        nextSendAt: null,
      },
    });
    await prisma.activity.create({
      data: {
        tenantId: c.tenantId,
        contactId: c.id,
        type: reason === 'UNSUBSCRIBE' ? 'EMAIL_UNSUBSCRIBED' : reason === 'HARD_BOUNCE' ? 'EMAIL_BOUNCED' : 'NOTE',
        meta: { reason, source: 'suppression' },
      },
    });
  }
}
