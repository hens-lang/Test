// RFC 8058 one-click unsubscribe: mailproviders POSTen naar deze URL zonder gebruikersinteractie.
import { NextResponse } from 'next/server';
import { verifyUnsubscribeToken } from '@/core/unsubscribe';
import { suppress } from '@/core/suppression';
import { rateLimit } from '@/lib/auth';

export async function POST(req: Request, { params }: { params: { token: string } }) {
  const ip = req.headers.get('x-forwarded-for') || 'unknown';
  if (!rateLimit(`unsub:${ip}`, 30, 60_000)) return new NextResponse('Too many requests', { status: 429 });
  const data = verifyUnsubscribeToken(decodeURIComponent(params.token));
  if (!data) return new NextResponse('Invalid token', { status: 400 });
  await suppress(data.tenantId, data.email, 'UNSUBSCRIBE');
  return new NextResponse('OK');
}
