import { NextResponse } from 'next/server';
import { destroySession } from '@/lib/auth';
import { getAppUrl } from '@/lib/env';

export async function POST() {
  await destroySession();
  return NextResponse.redirect(new URL('/login', getAppUrl()), 303);
}
