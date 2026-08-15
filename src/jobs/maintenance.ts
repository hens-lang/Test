// Onderhoudsjobs: dagelijkse reset, warm-up-stap, DNS-checks, e-mailvalidatie,
// TemplateStat-aggregatie, DataHealthRun en AVG-bewaartermijn.
import { prisma } from '@/lib/db';
import { advanceWarmup, warmupCapForDay } from '@/core/warmup';
import { checkDomain } from '@/core/dns-check';
import { validateEmail } from '@/core/validation';
import { templateHash, normalizeTemplate, isSafeForLibrary } from '@/core/anonymize';
import { findSuppressed } from '@/core/suppression';
import { notifyTeam } from './notify';
import { logger } from '@/lib/logger';

/** Dagelijks 00:05: sentToday/bouncedToday resetten (state in DB, herstart-veilig). */
export async function dailyReset(): Promise<void> {
  await prisma.mailbox.updateMany({
    data: { sentToday: 0, bouncedToday: 0, lastResetAt: new Date() },
  });
  // OOO-pauzes die verlopen zijn weer vrijgeven.
  await prisma.enrollment.updateMany({
    where: { oooPausedUntil: { lte: new Date() } },
    data: { oooPausedUntil: null },
  });
  logger.info('daily_reset_done');
}

/** Dagelijkse warm-up-stap (§7b). */
export async function warmupDaily(): Promise<void> {
  const warming = await prisma.mailbox.findMany({ where: { status: 'WARMING' } });
  for (const mb of warming) {
    const next = advanceWarmup({ warmupDay: mb.warmupDay, maxDailyCap: mb.maxDailyCap });
    await prisma.mailbox.update({
      where: { id: mb.id },
      data: {
        warmupDay: next.warmupDay,
        dailyCap: next.dailyCap,
        status: next.completed ? 'ACTIVE' : 'WARMING',
      },
    });
    if (next.completed) {
      await notifyTeam('warmup', 'Warm-up voltooid', `Mailbox ${mb.email} is opgewarmd en nu ACTIVE (cap ${next.dailyCap}/dag).`);
    } else if (next.warmupDay % 7 === 0) {
      await notifyTeam('warmup', 'Warm-up-mijlpaal', `Mailbox ${mb.email}: week ${next.warmupDay / 7} voltooid, nieuwe dagcap ${next.dailyCap}.`);
    }
  }
}

/** Elke 6 uur + handmatig: DNS-checks voor alle domeinen (§7a). */
export async function dnsCheckAll(): Promise<void> {
  const domains = await prisma.sendingDomain.findMany();
  for (const d of domains) {
    await dnsCheckOne(d.id);
  }
}

export async function dnsCheckOne(domainId: string): Promise<void> {
  const d = await prisma.sendingDomain.findUnique({ where: { id: domainId } });
  if (!d) return;
  try {
    const result = await checkDomain(d.domain, d.dkimSelector);
    // Zonder geldige SPF+DKIM mag een domein nooit versturen; de verzendpoort
    // checkt spfOk/dkimOk — hier alleen status bijhouden.
    let status = d.status;
    if (!result.spfOk || !result.dkimOk) {
      if (status === 'ACTIVE' || status === 'WARMING') status = 'PENDING';
    } else if (status === 'PENDING') {
      status = 'ACTIVE';
    }
    await prisma.sendingDomain.update({
      where: { id: d.id },
      data: {
        spfOk: result.spfOk,
        dkimOk: result.dkimOk,
        dmarcOk: result.dmarcOk,
        mxOk: result.mxOk,
        healthScore: result.healthScore,
        status,
        lastCheckedAt: new Date(),
      },
    });
  } catch (err) {
    logger.error({ domainId, err: String(err) }, 'dns_check_failed');
  }
}

/** E-mailvalidatie als job (§4). */
export async function validateContacts(tenantId?: string, limit = 200): Promise<number> {
  const contacts = await prisma.contact.findMany({
    where: { emailStatus: 'UNVERIFIED', ...(tenantId ? { tenantId } : {}) },
    take: limit,
  });
  for (const c of contacts) {
    const status = await validateEmail(c.email);
    await prisma.contact.update({
      where: { id: c.id },
      data: { emailStatus: status, emailCheckedAt: new Date() },
    });
  }
  return contacts.length;
}

/** Dagelijkse TemplateStat-aggregatie (§12) — geanonimiseerd, tenant-overstijgend. */
export async function aggregateTemplateStats(): Promise<void> {
  const campaigns = await prisma.campaign.findMany({
    where: { shareTemplates: true, tenant: { shareTemplates: true } },
    include: { sequenceSteps: true, tenant: { select: { industry: true } } },
  });
  for (const camp of campaigns) {
    const industry = camp.tenant.industry || 'algemeen';
    const sent = await prisma.activity.count({ where: { campaignId: camp.id, type: 'EMAIL_SENT' } });
    const replied = await prisma.activity.count({ where: { campaignId: camp.id, type: 'EMAIL_REPLIED' } });
    const positive = await prisma.lead.count({ where: { campaignId: camp.id } });
    if (sent === 0) continue;

    for (const step of camp.sequenceSteps) {
      const entries: { kind: 'SUBJECT' | 'BODY'; text: string }[] = [
        { kind: 'SUBJECT', text: step.subjectA },
        { kind: 'BODY', text: step.bodyA },
      ];
      if (step.subjectB) entries.push({ kind: 'SUBJECT', text: step.subjectB });
      if (step.bodyB) entries.push({ kind: 'BODY', text: step.bodyB });
      for (const entry of entries) {
        const sample = normalizeTemplate(entry.text);
        // Privacyregel hard afdwingen: alleen veilige, geanonimiseerde templates.
        if (!isSafeForLibrary(sample)) continue;
        const hash = templateHash(entry.text);
        await prisma.templateStat.upsert({
          where: { industry_kind_textHash: { industry, kind: entry.kind, textHash: hash } },
          create: {
            industry, kind: entry.kind, textHash: hash, textSample: sample.slice(0, 300),
            sentCount: sent, replyCount: replied, positiveCount: positive,
          },
          update: { sentCount: sent, replyCount: replied, positiveCount: positive, lastUsedAt: new Date() },
        });
      }
    }
  }
  logger.info('template_stats_aggregated');
}

/** Maandelijkse DataHealthRun (§13). */
export async function runDataHealth(tenantId: string): Promise<string> {
  const contacts = await prisma.contact.findMany({ where: { tenantId } });
  let newInvalid = 0;
  let newRisky = 0;
  let bouncesRemoved = 0;
  let suppressedCount = 0;

  const staleCutoff = new Date(Date.now() - 6 * 30 * 86400_000); // validatiestatus verloopt na 6 maanden
  const suppressed = await findSuppressed(tenantId, contacts.map((c) => c.email));

  for (const c of contacts) {
    if (suppressed.has(c.email.toLowerCase()) && c.emailStatus !== 'UNSUBSCRIBED' && c.emailStatus !== 'BOUNCED') {
      await prisma.contact.update({ where: { id: c.id }, data: { emailStatus: 'UNSUBSCRIBED' } });
      suppressedCount += 1;
      continue;
    }
    if (c.emailStatus === 'BOUNCED') {
      bouncesRemoved += 1;
      continue;
    }
    const needsCheck = c.emailStatus === 'UNVERIFIED' || !c.emailCheckedAt || c.emailCheckedAt < staleCutoff;
    if (!needsCheck) continue;
    const status = await validateEmail(c.email);
    if (status !== c.emailStatus) {
      if (status === 'INVALID') newInvalid += 1;
      if (status === 'RISKY') newRisky += 1;
    }
    await prisma.contact.update({
      where: { id: c.id },
      data: { emailStatus: status, emailCheckedAt: new Date() },
    });
  }

  const report = {
    samenvatting: `Gecontroleerd: ${contacts.length} contacten. Nieuw ongeldig: ${newInvalid}. Nieuw risicovol: ${newRisky}. Bounces opgeschoond: ${bouncesRemoved}. Gesupprimeerd: ${suppressedCount}.`,
    details: { gecontroleerd: contacts.length, nieuwOngeldig: newInvalid, nieuwRisicovol: newRisky, bounces: bouncesRemoved, gesupprimeerd: suppressedCount },
  };
  const run = await prisma.dataHealthRun.create({
    data: {
      tenantId,
      contactsChecked: contacts.length,
      newInvalid,
      newRisky,
      bouncesRemoved,
      suppressed: suppressedCount,
      enriched: 0,
      reportJson: report,
    },
  });
  return run.id;
}

/** AVG-bewaartermijn (§15): prospects zonder activiteit > 18 maanden anonimiseren. */
export async function retentionSweep(months = 18): Promise<number> {
  const cutoff = new Date(Date.now() - months * 30 * 86400_000);
  const stale = await prisma.contact.findMany({
    where: {
      createdAt: { lt: cutoff },
      activities: { none: { occurredAt: { gte: cutoff } } },
    },
    take: 500,
  });
  for (const c of stale) {
    await anonymizeContact(c.id);
  }
  return stale.length;
}

/** Recht op vergetelheid (§15): hard-delete + anonimiseren van gerelateerde data. */
export async function anonymizeContact(contactId: string): Promise<void> {
  const c = await prisma.contact.findUnique({ where: { id: contactId } });
  if (!c) return;
  await prisma.$transaction([
    prisma.message.updateMany({
      where: { enrollment: { contactId } },
      data: { body: '[verwijderd op verzoek]', subject: '[verwijderd]', fromEmail: null, toEmail: null },
    }),
    prisma.referral.updateMany({
      where: { sourceContactId: contactId },
      data: { suggestedName: null, suggestedEmail: null, rawSnippet: '[verwijderd op verzoek]' },
    }),
    prisma.activity.updateMany({ where: { contactId }, data: { meta: {} } }),
    prisma.contact.delete({ where: { id: contactId } }),
  ]);
}
