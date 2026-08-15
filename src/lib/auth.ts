import 'server-only';
import { cookies } from 'next/headers';
import { SignJWT, jwtVerify } from 'jose';
import bcrypt from 'bcryptjs';
import { prisma } from './db';
import { getSessionSecret } from './env';
import type { Role } from '@prisma/client';

const COOKIE_NAME = 'link_session';
const SESSION_TTL_HOURS = 12;

export interface SessionUser {
  userId: string;
  tenantId: string | null;
  role: Role;
  name: string;
  email: string;
}

function secretKey() {
  return new TextEncoder().encode(getSessionSecret());
}

export async function hashPassword(plain: string): Promise<string> {
  return bcrypt.hash(plain, 12);
}

export async function verifyPassword(plain: string, hash: string): Promise<boolean> {
  return bcrypt.compare(plain, hash);
}

export async function createSession(user: SessionUser): Promise<void> {
  const token = await new SignJWT({ ...user })
    .setProtectedHeader({ alg: 'HS256' })
    .setIssuedAt()
    .setExpirationTime(`${SESSION_TTL_HOURS}h`)
    .sign(secretKey());
  cookies().set(COOKIE_NAME, token, {
    httpOnly: true,
    sameSite: 'lax',
    secure: process.env.NODE_ENV === 'production',
    path: '/',
    maxAge: SESSION_TTL_HOURS * 3600,
  });
}

export async function destroySession(): Promise<void> {
  cookies().delete(COOKIE_NAME);
}

export async function getSession(): Promise<SessionUser | null> {
  const token = cookies().get(COOKIE_NAME)?.value;
  if (!token) return null;
  try {
    const { payload } = await jwtVerify(token, secretKey());
    return {
      userId: payload.userId as string,
      tenantId: (payload.tenantId as string | null) ?? null,
      role: payload.role as Role,
      name: payload.name as string,
      email: payload.email as string,
    };
  } catch {
    return null;
  }
}

/** Vereist een ingelogde LINK.-medewerker (ADMIN of MANAGER). */
export async function requireStaff(): Promise<SessionUser> {
  const s = await getSession();
  if (!s || (s.role !== 'ADMIN' && s.role !== 'MANAGER')) throw new AuthError('Geen toegang');
  return s;
}

export async function requireAdmin(): Promise<SessionUser> {
  const s = await getSession();
  if (!s || s.role !== 'ADMIN') throw new AuthError('Alleen voor beheerders');
  return s;
}

/** Vereist een klantgebruiker; geeft diens tenantId terug. */
export async function requireClient(): Promise<SessionUser & { tenantId: string }> {
  const s = await getSession();
  if (!s || s.role !== 'CLIENT' || !s.tenantId) throw new AuthError('Geen toegang');
  return s as SessionUser & { tenantId: string };
}

export class AuthError extends Error {}

// Eenvoudige in-memory rate-limiter voor login en publieke endpoints.
// Bewust simpel (één app-proces per spec §16); state hoeft niet te overleven bij herstart.
const buckets = new Map<string, { count: number; resetAt: number }>();

export function rateLimit(key: string, max: number, windowMs: number): boolean {
  const now = Date.now();
  const b = buckets.get(key);
  if (!b || b.resetAt < now) {
    buckets.set(key, { count: 1, resetAt: now + windowMs });
    return true;
  }
  b.count += 1;
  return b.count <= max;
}

export async function audit(
  userId: string | null,
  action: string,
  entity: string,
  entityId: string,
  meta: Record<string, unknown> = {},
): Promise<void> {
  await prisma.auditLog.create({
    data: { userId, action, entity, entityId, meta: meta as object },
  });
}
