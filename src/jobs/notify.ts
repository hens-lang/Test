// Notificaties (§14): nieuwe lead, referral-suggestie, guardrail-trigger,
// warm-up-mijlpaal, wekelijkse samenvatting. E-mail naar het LINK.-team en
// optioneel een webhook per tenant. In demo-modus alleen loggen.
import nodemailer from 'nodemailer';
import { prisma } from '@/lib/db';
import { getSendMode } from '@/lib/env';
import { logger } from '@/lib/logger';

export type NotificationKind = 'lead' | 'referral' | 'guardrail' | 'warmup' | 'weekly';

export async function notifyTeam(kind: NotificationKind, subject: string, body: string, tenantId?: string): Promise<void> {
  logger.info({ kind, subject, tenantId }, 'notification');

  if (tenantId) {
    const tenant = await prisma.tenant.findUnique({ where: { id: tenantId }, select: { webhookUrl: true } });
    if (tenant?.webhookUrl) {
      fetch(tenant.webhookUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ kind, subject, body, tenantId, at: new Date().toISOString() }),
        signal: AbortSignal.timeout(5000),
      }).catch((err) => logger.warn({ err: String(err) }, 'webhook_failed'));
    }
  }

  if (getSendMode() === 'demo') return;
  const host = process.env.NOTIFY_SMTP_HOST;
  if (!host) return;
  try {
    const transporter = nodemailer.createTransport({
      host,
      port: Number(process.env.NOTIFY_SMTP_PORT || 587),
      auth: process.env.NOTIFY_SMTP_USER
        ? { user: process.env.NOTIFY_SMTP_USER, pass: process.env.NOTIFY_SMTP_PASS }
        : undefined,
    });
    await transporter.sendMail({
      from: process.env.NOTIFY_FROM || 'platform@linkgrp.nl',
      to: process.env.NOTIFY_FROM || 'platform@linkgrp.nl',
      subject: `[LINK. Outreach] ${subject}`,
      text: body,
    });
  } catch (err) {
    logger.error({ err: String(err) }, 'notify_mail_failed');
  }
}
