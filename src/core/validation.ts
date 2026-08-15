// E-mailvalidatie: syntax, rolgebaseerde adressen, wegwerpdomeinen, MX-lookup.
import { promises as dns } from 'dns';
import type { EmailStatus } from '@prisma/client';

const EMAIL_RE =
  /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$/;

export const ROLE_LOCALPARTS = new Set([
  'info', 'sales', 'admin', 'administratie', 'office', 'contact', 'support', 'hello', 'hallo',
  'mail', 'post', 'noreply', 'no-reply', 'webmaster', 'hr', 'jobs', 'marketing', 'billing',
  'facturatie', 'receptie', 'secretariaat', 'klantenservice', 'service', 'verkoop', 'inkoop',
]);

export const DISPOSABLE_DOMAINS = new Set([
  'mailinator.com', 'guerrillamail.com', '10minutemail.com', 'tempmail.com', 'temp-mail.org',
  'yopmail.com', 'trashmail.com', 'getnada.com', 'sharklasers.com', 'dispostable.com',
  'maildrop.cc', 'throwawaymail.com', 'fakeinbox.com', 'spamgourmet.com', 'mytemp.email',
]);

export function isValidSyntax(email: string): boolean {
  return EMAIL_RE.test(email) && email.length <= 254;
}

export function isRoleBased(email: string): boolean {
  const local = email.split('@')[0]?.toLowerCase() ?? '';
  return ROLE_LOCALPARTS.has(local);
}

export function isDisposable(email: string): boolean {
  const domain = email.split('@')[1]?.toLowerCase() ?? '';
  return DISPOSABLE_DOMAINS.has(domain);
}

export async function hasMx(domain: string): Promise<boolean> {
  try {
    const records = await dns.resolveMx(domain);
    return records.length > 0;
  } catch {
    return false;
  }
}

/**
 * Pure classificatie op basis van reeds opgehaalde MX-info — unit-testbaar.
 * VALID mag altijd de campagne in; RISKY alleen na expliciete keuze; rest nooit.
 */
export function classifyEmail(email: string, mxOk: boolean): EmailStatus {
  const e = email.trim().toLowerCase();
  if (!isValidSyntax(e)) return 'INVALID';
  if (isDisposable(e)) return 'INVALID';
  if (!mxOk) return 'INVALID';
  if (isRoleBased(e)) return 'RISKY';
  return 'VALID';
}

export async function validateEmail(email: string): Promise<EmailStatus> {
  const e = email.trim().toLowerCase();
  if (!isValidSyntax(e)) return 'INVALID';
  if (isDisposable(e)) return 'INVALID';
  const domain = e.split('@')[1];
  const mxOk = await hasMx(domain);
  return classifyEmail(e, mxOk);
}

/** Statussen die (onder voorwaarden) een campagne in mogen. */
export function isEnrollable(status: EmailStatus, allowRisky: boolean): boolean {
  if (status === 'VALID') return true;
  if (status === 'RISKY' && allowRisky) return true;
  return false;
}
