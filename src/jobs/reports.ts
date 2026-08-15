// Rapportages (§13/§14): weekrapport (maandag 08:00) en maandelijks waarderapport
// (1e van de maand). Zelfde cijfers als het dashboard: gedeelde query-laag (core/stats).
import nodemailer from 'nodemailer';
import { prisma } from '@/lib/db';
import { funnelStats, weeklyTrend, dataHealthSummary, industryAvgReplyRate } from '@/core/stats';
import { getSendMode } from '@/lib/env';
import { logger } from '@/lib/logger';

function pct(n: number): string {
  return `${(n * 100).toFixed(1)}%`;
}

function htmlShell(title: string, brandColor: string, inner: string): string {
  return `<!doctype html><html lang="nl"><body style="font-family:Arial,sans-serif;background:#f4f5f7;margin:0;padding:24px">
<div style="max-width:640px;margin:0 auto;background:#fff;border-radius:8px;overflow:hidden">
<div style="background:${brandColor};color:#fff;padding:20px 28px"><h1 style="margin:0;font-size:20px">${title}</h1></div>
<div style="padding:28px">${inner}</div>
<div style="padding:16px 28px;color:#888;font-size:12px;border-top:1px solid #eee">LINK. Outreach — automatisch gegenereerd rapport</div>
</div></body></html>`;
}

function statRow(label: string, value: string): string {
  return `<tr><td style="padding:8px 0;color:#555">${label}</td><td style="padding:8px 0;text-align:right;font-weight:bold">${value}</td></tr>`;
}

export async function buildWeeklyReport(tenantId: string): Promise<{ subject: string; html: string }> {
  const tenant = await prisma.tenant.findUniqueOrThrow({ where: { id: tenantId } });
  const weekAgo = new Date(Date.now() - 7 * 86400_000);
  const stats = await funnelStats(tenantId, weekAgo);
  const leads = await prisma.lead.findMany({
    where: { tenantId, createdAt: { gte: weekAgo } },
    include: { contact: { include: { company: true } } },
    take: 20,
  });

  const leadRows = leads
    .map((l) => `<li>${l.contact.firstName} ${l.contact.lastName} — ${l.contact.company.name}${l.viaReferral ? ' <em>(via doorverwijzing)</em>' : ''}</li>`)
    .join('');
  const inner = `
<p>Beste ${tenant.name},</p>
<p>Hieronder de resultaten van de afgelopen week.</p>
<table style="width:100%;border-collapse:collapse">
${statRow('Benaderde prospects', String(stats.approached))}
${statRow('Verzonden mails', String(stats.sent))}
${statRow('Reacties', String(stats.replied))}
${statRow('Reply-rate', pct(stats.replyRate))}
${statRow('Nieuwe leads', String(stats.leads))}
${statRow('waarvan via doorverwijzing', String(stats.leadsViaReferral))}
</table>
${leads.length > 0 ? `<h3>Nieuwe leads</h3><ul>${leadRows}</ul>` : ''}
<p style="color:#888;font-size:12px">Open-rates zijn indicatief en door privacy-maatregelen van mailproviders niet betrouwbaar; wij sturen daarom op reacties en leads.</p>`;
  return {
    subject: `Weekrapportage ${tenant.name} — ${stats.leads} nieuwe lead(s)`,
    html: htmlShell(`Weekrapportage ${tenant.name}`, tenant.brandColor || '#1d4ed8', inner),
  };
}

export async function buildMonthlyValueReport(tenantId: string): Promise<{ subject: string; html: string }> {
  const tenant = await prisma.tenant.findUniqueOrThrow({ where: { id: tenantId } });
  const monthAgo = new Date(Date.now() - 30 * 86400_000);
  const stats = await funnelStats(tenantId, monthAgo);
  const health = await dataHealthSummary(tenantId);
  const benchmark = tenant.industry ? await industryAvgReplyRate(tenant.industry) : null;
  const leads = await prisma.lead.findMany({
    where: { tenantId, createdAt: { gte: monthAgo } },
    include: { contact: { include: { company: true } } },
    take: 50,
  });
  const trend = await weeklyTrend(tenantId, 4);

  const latestSnapshot = await prisma.insightSnapshot.findFirst({
    where: { tenantId },
    orderBy: { period: 'desc' },
  });
  const conclusions = (latestSnapshot?.conclusions as string[] | null) ?? [];

  const leadRows = leads
    .map((l) => `<li><strong>${l.contact.firstName} ${l.contact.lastName}</strong> — ${l.contact.company.name}${l.viaReferral ? ' <em>(via doorverwijzing)</em>' : ''}</li>`)
    .join('');
  const trendRows = trend
    .map((t) => statRow(`Week van ${t.weekStart}`, `${t.sent} verzonden · ${t.replied} reacties · ${t.leads} leads`))
    .join('');
  const inner = `
<p>Beste ${tenant.name},</p>
<p>Uw maand in cijfers — wat uw abonnement deze maand heeft opgeleverd.</p>
<h3>Resultaten</h3>
<table style="width:100%;border-collapse:collapse">
${statRow('Geleverde leads', String(stats.leads))}
${statRow('waarvan via doorverwijzing', String(stats.leadsViaReferral))}
${statRow('Benaderde prospects', String(stats.approached))}
${statRow('Reply-rate', pct(stats.replyRate) + (benchmark !== null ? ` (branchegemiddelde: ${pct(benchmark)})` : ''))}
</table>
${leads.length > 0 ? `<h3>Uw leads deze maand</h3><ul>${leadRows}</ul>` : ''}
${conclusions.length > 0 ? `<h3>Wat wij deze maand over uw markt leerden</h3><ul>${conclusions.map((c) => `<li>${c}</li>`).join('')}</ul>` : ''}
<h3>Verloop per week</h3>
<table style="width:100%;border-collapse:collapse">${trendRows}</table>
<h3>Datahygiëne</h3>
<table style="width:100%;border-collapse:collapse">
${statRow('Contacten in uw bestand', String(health.totalContacts))}
${statRow('Gevalideerd', `${health.validPercent}%`)}
${statRow('Opgeschoond deze maand', String(health.cleanedThisMonth))}
</table>
<p>Komende maand gaan we door met de lopende campagnes en de maandelijkse datacontrole.</p>`;
  return {
    subject: `Uw maand in cijfers — ${stats.leads} geleverde lead(s)`,
    html: htmlShell(`Uw maand in cijfers · ${tenant.name}`, tenant.brandColor || '#1d4ed8', inner),
  };
}

async function deliverReport(tenantId: string, subject: string, html: string): Promise<void> {
  const tenant = await prisma.tenant.findUniqueOrThrow({ where: { id: tenantId } });
  const recipients = (tenant.reportRecipients || '').split(',').map((r) => r.trim()).filter(Boolean);
  if (getSendMode() === 'demo' || recipients.length === 0 || !process.env.NOTIFY_SMTP_HOST) {
    logger.info({ tenantId, subject }, 'report_generated_not_sent_demo');
    return;
  }
  const transporter = nodemailer.createTransport({
    host: process.env.NOTIFY_SMTP_HOST,
    port: Number(process.env.NOTIFY_SMTP_PORT || 587),
    auth: process.env.NOTIFY_SMTP_USER
      ? { user: process.env.NOTIFY_SMTP_USER, pass: process.env.NOTIFY_SMTP_PASS }
      : undefined,
  });
  await transporter.sendMail({
    from: process.env.NOTIFY_FROM || 'platform@linkgrp.nl',
    to: recipients,
    subject,
    html,
  });
}

export async function sendWeeklyReports(): Promise<void> {
  const tenants = await prisma.tenant.findMany({ select: { id: true } });
  for (const t of tenants) {
    const report = await buildWeeklyReport(t.id);
    await deliverReport(t.id, report.subject, report.html);
  }
}

export async function sendMonthlyReports(): Promise<void> {
  const tenants = await prisma.tenant.findMany({ select: { id: true } });
  for (const t of tenants) {
    const report = await buildMonthlyValueReport(t.id);
    await deliverReport(t.id, report.subject, report.html);
  }
}
