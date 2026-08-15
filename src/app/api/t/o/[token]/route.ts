// Tracking-pixel (open-registratie). Token = trackingToken uit de EMAIL_SENT-activity.
import { NextResponse } from 'next/server';
import { prisma } from '@/lib/db';

const GIF = Buffer.from('R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7', 'base64');

export async function GET(_req: Request, { params }: { params: { token: string } }) {
  const token = params.token.replace(/\.gif$/, '');
  const sent = await prisma.activity.findFirst({
    where: { type: 'EMAIL_SENT', meta: { path: ['trackingToken'], equals: token } },
  });
  if (sent) {
    const already = await prisma.activity.findFirst({
      where: { type: 'EMAIL_OPENED', meta: { path: ['trackingToken'], equals: token } },
    });
    if (!already) {
      await prisma.activity.create({
        data: {
          tenantId: sent.tenantId, contactId: sent.contactId, campaignId: sent.campaignId,
          enrollmentId: sent.enrollmentId, type: 'EMAIL_OPENED', meta: { trackingToken: token },
        },
      });
    }
  }
  return new NextResponse(GIF, { headers: { 'Content-Type': 'image/gif', 'Cache-Control': 'no-store' } });
}
