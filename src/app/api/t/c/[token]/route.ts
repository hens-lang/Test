// Klik-tracking: registreert de klik en stuurt door naar de originele URL.
import { NextResponse } from 'next/server';
import { prisma } from '@/lib/db';

export async function GET(req: Request, { params }: { params: { token: string } }) {
  const url = new URL(req.url).searchParams.get('u');
  if (!url || !/^https?:\/\//.test(url)) return new NextResponse('Bad request', { status: 400 });
  const sent = await prisma.activity.findFirst({
    where: { type: 'EMAIL_SENT', meta: { path: ['trackingToken'], equals: params.token } },
  });
  if (sent) {
    await prisma.activity.create({
      data: {
        tenantId: sent.tenantId, contactId: sent.contactId, campaignId: sent.campaignId,
        enrollmentId: sent.enrollmentId, type: 'EMAIL_CLICKED', meta: { trackingToken: params.token, url },
      },
    });
  }
  return NextResponse.redirect(url, 302);
}
