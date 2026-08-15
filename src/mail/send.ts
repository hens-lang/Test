// Verzendengine (§7c): alle uitgaande mail loopt hierdoorheen.
// - Demo-modus (default): niets wordt echt verstuurd; de mail wordt volledig
//   gerenderd en als verzonden gelogd, zichtbaar in de UI.
// - Live-modus: nodemailer via de SMTP van de mailbox.
// De harde verzendpoort (canSend) zit in de verzendjob, vóór deze functie.
import nodemailer from 'nodemailer';
import { randomUUID } from 'crypto';
import { decryptSecret } from '@/lib/crypto';
import { getSendMode, getAppUrl } from '@/lib/env';
import { listUnsubscribeHeaders, unsubscribeUrl } from '@/core/unsubscribe';
import { logger } from '@/lib/logger';
import type { Mailbox } from '@prisma/client';

export interface OutgoingMail {
  tenantId: string;
  to: string;
  subject: string;
  bodyText: string; // plain-text-first
  senderAddress: string; // fysiek afzenderadres (verplicht in footer)
  inReplyTo?: string;
  references?: string[];
  trackingEnabled?: boolean;
  trackingToken?: string; // koppelt open/klik aan enrollment
  isReply?: boolean; // replies: geen afmeldfooter/tracking nodig
}

export interface SendResult {
  ok: boolean;
  messageId: string;
  error?: string;
  renderedText: string;
  renderedHtml: string;
}

export function buildFooter(mail: Pick<OutgoingMail, 'tenantId' | 'to' | 'senderAddress'>): string {
  const url = unsubscribeUrl(mail.tenantId, mail.to);
  return `\n\n--\n${mail.senderAddress}\nLiever geen e-mail meer ontvangen? Afmelden: ${url}`;
}

function escapeHtml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

/** Minimalistische HTML-variant: alinea's + max 1 tracking-pixel, links via tracking-domein. */
export function buildHtml(text: string, opts: { trackingPixelUrl?: string; trackingLinkBase?: string }): string {
  let html = escapeHtml(text)
    .split(/\n\n+/)
    .map((p) => `<p>${p.replace(/\n/g, '<br>')}</p>`)
    .join('\n');
  if (opts.trackingLinkBase) {
    html = html.replace(/https?:\/\/[^\s<>"']+/g, (url) =>
      url.startsWith(opts.trackingLinkBase!)
        ? `<a href="${url}">${url}</a>`
        : `<a href="${opts.trackingLinkBase}?u=${encodeURIComponent(url)}">${url}</a>`,
    );
  }
  if (opts.trackingPixelUrl) {
    html += `\n<img src="${opts.trackingPixelUrl}" width="1" height="1" alt="">`;
  }
  return `<!doctype html><html><body style="font-family:Arial,sans-serif;font-size:14px;color:#1a1a1a">${html}</body></html>`;
}

export async function sendMail(mailbox: Mailbox, mail: OutgoingMail): Promise<SendResult> {
  const messageId = `<${randomUUID()}@${mailbox.email.split('@')[1]}>`;
  const withFooter = mail.isReply ? mail.bodyText : mail.bodyText + buildFooter(mail);
  const tracking = mail.trackingEnabled && mail.trackingToken && !mail.isReply;
  const html = buildHtml(withFooter, {
    trackingPixelUrl: tracking ? `${getAppUrl()}/api/t/o/${mail.trackingToken}.gif` : undefined,
    trackingLinkBase: tracking ? `${getAppUrl()}/api/t/c/${mail.trackingToken}` : undefined,
  });

  if (getSendMode() === 'demo') {
    logger.info({ to: '[redacted]', mailbox: mailbox.id, demo: true }, 'mail_demo_send');
    return { ok: true, messageId, renderedText: withFooter, renderedHtml: html };
  }

  try {
    const transporter = nodemailer.createTransport({
      host: mailbox.smtpHost,
      port: mailbox.smtpPort,
      secure: mailbox.smtpPort === 465,
      auth: { user: mailbox.smtpUser, pass: decryptSecret(mailbox.smtpPassEncrypted) },
    });
    const headers: Record<string, string> = mail.isReply
      ? {}
      : listUnsubscribeHeaders(mail.tenantId, mail.to, mailbox.email);
    await transporter.sendMail({
      from: { name: mailbox.displayName, address: mailbox.email },
      to: mail.to,
      subject: mail.subject,
      text: withFooter,
      html,
      messageId,
      inReplyTo: mail.inReplyTo,
      references: mail.references,
      headers,
    });
    return { ok: true, messageId, renderedText: withFooter, renderedHtml: html };
  } catch (err) {
    logger.error({ mailbox: mailbox.id, err: String(err) }, 'smtp_send_failed');
    return { ok: false, messageId, error: String(err), renderedText: withFooter, renderedHtml: html };
  }
}
