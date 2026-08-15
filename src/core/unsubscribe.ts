// One-click unsubscribe (RFC 8058): publiek, zonder login, via ondertekende token.
import { createHmac, timingSafeEqual } from 'crypto';
import { getSessionSecret, getAppUrl } from '@/lib/env';

function sign(payload: string): string {
  return createHmac('sha256', getSessionSecret()).update(payload).digest('base64url');
}

export function makeUnsubscribeToken(tenantId: string, email: string): string {
  const payload = Buffer.from(JSON.stringify({ t: tenantId, e: email.toLowerCase() })).toString('base64url');
  return `${payload}.${sign(payload)}`;
}

export function verifyUnsubscribeToken(token: string): { tenantId: string; email: string } | null {
  const [payload, sig] = token.split('.');
  if (!payload || !sig) return null;
  const expected = sign(payload);
  try {
    if (!timingSafeEqual(Buffer.from(sig), Buffer.from(expected))) return null;
    const data = JSON.parse(Buffer.from(payload, 'base64url').toString());
    if (typeof data.t !== 'string' || typeof data.e !== 'string') return null;
    return { tenantId: data.t, email: data.e };
  } catch {
    return null;
  }
}

export function unsubscribeUrl(tenantId: string, email: string): string {
  return `${getAppUrl()}/afmelden/${encodeURIComponent(makeUnsubscribeToken(tenantId, email))}`;
}

export function listUnsubscribeHeaders(tenantId: string, email: string, mailboxEmail: string): Record<string, string> {
  const url = unsubscribeUrl(tenantId, email);
  return {
    'List-Unsubscribe': `<mailto:${mailboxEmail}?subject=unsubscribe>, <${url}>`,
    'List-Unsubscribe-Post': 'List-Unsubscribe=One-Click',
  };
}
