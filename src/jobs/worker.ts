// pg-boss worker (§2): alle verzendingen, warm-up-stappen, DNS-checks, AI-jobs
// en IMAP-polls lopen als jobs op dezelfde Postgres. Start met `npm run worker`.
import PgBoss from 'pg-boss';
import { prisma } from '@/lib/db';
import { logger, reportError } from '@/lib/logger';
import { processSend } from './send';
import { planDueSends } from './scheduler';
import { pollMailbox } from './imap';
import { generateOpener, summarizeWebsite } from '@/personalization/engine';
import {
  dailyReset,
  warmupDaily,
  dnsCheckAll,
  dnsCheckOne,
  validateContacts,
  aggregateTemplateStats,
  runDataHealth,
  retentionSweep,
} from './maintenance';
import { sendWeeklyReports, sendMonthlyReports } from './reports';

export const QUEUES = {
  SEND: 'send-email',
  PERSONALIZE: 'personalize',
  WEBSITE_SUMMARY: 'website-summary',
  VALIDATE: 'validate-contacts',
  DNS_CHECK: 'dns-check',
  IMAP_POLL: 'imap-poll',
  DATA_HEALTH: 'data-health',
} as const;

async function main() {
  const boss = new PgBoss({ connectionString: process.env.DATABASE_URL, schema: 'pgboss' });
  boss.on('error', (err) => reportError(err, { source: 'pg-boss' }));
  await boss.start();

  for (const q of Object.values(QUEUES)) await boss.createQueue(q);

  // --- Wachtrij-handlers ---
  await boss.work<{ enrollmentId: string }>(QUEUES.SEND, async ([job]) => {
    await processSend(job.data.enrollmentId);
  });
  await boss.work<{ enrollmentId: string }>(QUEUES.PERSONALIZE, { batchSize: 1 }, async ([job]) => {
    await generateOpener(job.data.enrollmentId);
  });
  await boss.work<{ companyId: string }>(QUEUES.WEBSITE_SUMMARY, async ([job]) => {
    await summarizeWebsite(job.data.companyId);
  });
  await boss.work<{ tenantId?: string }>(QUEUES.VALIDATE, async ([job]) => {
    await validateContacts(job.data.tenantId);
  });
  await boss.work<{ domainId?: string }>(QUEUES.DNS_CHECK, async ([job]) => {
    if (job.data.domainId) await dnsCheckOne(job.data.domainId);
    else await dnsCheckAll();
  });
  await boss.work<{ mailboxId: string }>(QUEUES.IMAP_POLL, async ([job]) => {
    await pollMailbox(job.data.mailboxId);
  });
  await boss.work<{ tenantId: string }>(QUEUES.DATA_HEALTH, async ([job]) => {
    await runDataHealth(job.data.tenantId);
  });

  // --- Cron-schema's (tijden in UTC; Europe/Amsterdam is UTC+1/+2) ---
  await boss.schedule(QUEUES.DNS_CHECK, '0 */6 * * *', {}); // elke 6 uur

  const cron = async (name: string, schedule: string, fn: () => Promise<unknown>) => {
    await boss.createQueue(name);
    await boss.work(name, async () => {
      await fn();
    });
    await boss.schedule(name, schedule, {}, { tz: 'Europe/Amsterdam' });
  };

  await cron('cron-daily-reset', '5 0 * * *', dailyReset);
  await cron('cron-warmup-daily', '15 0 * * *', warmupDaily);
  await cron('cron-template-stats', '30 1 * * *', aggregateTemplateStats);
  await cron('cron-weekly-report', '0 8 * * 1', sendWeeklyReports);
  await cron('cron-monthly-report', '0 8 1 * *', sendMonthlyReports);
  await cron('cron-retention', '0 3 * * 0', () => retentionSweep());
  await cron('cron-monthly-datahealth', '0 6 1 * *', async () => {
    const tenants = await prisma.tenant.findMany({ select: { id: true } });
    for (const t of tenants) await runDataHealth(t.id);
  });

  // Scheduler-lus: elke minuut kijken of er mails ingepland moeten worden.
  await cron('cron-plan-sends', '* * * * *', async () => {
    const planned = await planDueSends();
    for (const p of planned) {
      await boss.send(QUEUES.SEND, { enrollmentId: p.enrollmentId }, { startAfter: p.sendAt });
    }
  });

  // IMAP-poll elke 2 minuten per actieve mailbox.
  await cron('cron-imap-tick', '*/2 * * * *', async () => {
    const mailboxes = await prisma.mailbox.findMany({
      where: { status: { in: ['ACTIVE', 'WARMING'] } },
      select: { id: true },
    });
    for (const mb of mailboxes) {
      await boss.send(QUEUES.IMAP_POLL, { mailboxId: mb.id }, { singletonKey: mb.id, singletonSeconds: 60 });
    }
  });

  logger.info('worker_started');
}

main().catch((err) => {
  reportError(err, { source: 'worker_main' });
  process.exit(1);
});
