'use server';
// Server actions voor het interne beheer. Elke action controleert zelf de rol.
import { revalidatePath } from 'next/cache';
import { redirect } from 'next/navigation';
import { prisma } from '@/lib/db';
import { tenantDb } from '@/lib/tenancy';
import { requireStaff, requireAdmin, hashPassword, audit } from '@/lib/auth';
import { validateEmail, isEnrollable } from '@/core/validation';
import { findSuppressed, suppress } from '@/core/suppression';
import { lintSequence, hasBlockers } from '@/core/lint';
import { renderTemplate, buildVars, extractVariables } from '@/core/template';
import { assignMailboxesRoundRobin } from '@/core/planner';
import { encryptSecret } from '@/lib/crypto';
import { clampMaxCap, warmupCapForDay, DEFAULT_MAX_CAP } from '@/core/warmup';
import { dnsCheckOne } from '@/jobs/maintenance';
import { generateOpener } from '@/personalization/engine';
import { processInbound } from '@/jobs/inbound';
import { processSend } from '@/jobs/send';
import { sendMail } from '@/mail/send';
import { runDataHealth } from '@/jobs/maintenance';
import Papa from 'papaparse';

// ---------- Tenants ----------

export async function createTenant(formData: FormData) {
  const user = await requireAdmin();
  const name = String(formData.get('name') || '').trim();
  const slug = name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
  const tenant = await prisma.tenant.create({
    data: {
      name,
      slug,
      industry: String(formData.get('industry') || '') || null,
      senderAddress: String(formData.get('senderAddress') || '') || null,
      brandColor: String(formData.get('brandColor') || '') || null,
    },
  });
  await audit(user.userId, 'tenant_created', 'Tenant', tenant.id);
  revalidatePath('/beheer/tenants');
}

export async function updateTenant(formData: FormData) {
  const user = await requireStaff();
  const id = String(formData.get('id'));
  await prisma.tenant.update({
    where: { id },
    data: {
      toneOfVoice: String(formData.get('toneOfVoice') || '') || null,
      industry: String(formData.get('industry') || '') || null,
      senderAddress: String(formData.get('senderAddress') || '') || null,
      brandColor: String(formData.get('brandColor') || '') || null,
      webhookUrl: String(formData.get('webhookUrl') || '') || null,
      reportRecipients: String(formData.get('reportRecipients') || '') || null,
    },
  });
  await audit(user.userId, 'tenant_updated', 'Tenant', id);
  revalidatePath(`/beheer/tenants/${id}`);
}

export async function createUser(formData: FormData) {
  const admin = await requireAdmin();
  const email = String(formData.get('email') || '').trim().toLowerCase();
  const created = await prisma.user.create({
    data: {
      email,
      name: String(formData.get('name') || ''),
      role: formData.get('role') === 'CLIENT' ? 'CLIENT' : formData.get('role') === 'ADMIN' ? 'ADMIN' : 'MANAGER',
      tenantId: String(formData.get('tenantId') || '') || null,
      passwordHash: await hashPassword(String(formData.get('password') || '')),
    },
  });
  await audit(admin.userId, 'user_created', 'User', created.id);
  revalidatePath('/beheer/tenants');
}

// ---------- Prospect-import (§4) ----------

export interface ImportReport {
  total: number;
  imported: number;
  updated: number;
  suppressed: number;
  errors: { row: number; message: string }[];
}

export async function importContacts(formData: FormData): Promise<void> {
  const user = await requireStaff();
  const tenantId = String(formData.get('tenantId'));
  const csv = String(formData.get('csv') || '');
  const mapping = {
    firstName: String(formData.get('map_firstName') || 'voornaam'),
    lastName: String(formData.get('map_lastName') || 'achternaam'),
    email: String(formData.get('map_email') || 'email'),
    company: String(formData.get('map_company') || 'bedrijf'),
    domain: String(formData.get('map_domain') || 'domein'),
    title: String(formData.get('map_title') || 'functie'),
    city: String(formData.get('map_city') || 'stad'),
    industry: String(formData.get('map_industry') || 'branche'),
  };
  const dryRun = formData.get('dryRun') === '1';

  const parsed = Papa.parse<Record<string, string>>(csv.trim(), { header: true, skipEmptyLines: true });
  const rows = parsed.data;
  const report: ImportReport = { total: rows.length, imported: 0, updated: 0, suppressed: 0, errors: [] };

  const emails = rows.map((r) => (r[mapping.email] || '').trim().toLowerCase()).filter(Boolean);
  const suppressedSet = await findSuppressed(tenantId, emails);
  const db = tenantDb(tenantId);

  for (let i = 0; i < rows.length; i++) {
    const row = rows[i];
    const email = (row[mapping.email] || '').trim().toLowerCase();
    const companyName = (row[mapping.company] || '').trim();
    const domain = ((row[mapping.domain] || '').trim() || email.split('@')[1] || '').toLowerCase();
    if (!email || !email.includes('@')) {
      report.errors.push({ row: i + 1, message: 'Geen geldig e-mailadres' });
      continue;
    }
    if (!companyName) {
      report.errors.push({ row: i + 1, message: 'Bedrijfsnaam ontbreekt' });
      continue;
    }
    if (suppressedSet.has(email)) {
      report.suppressed += 1;
      continue; // nooit enrollen; ook niet importeren als actief contact
    }
    if (dryRun) {
      report.imported += 1;
      continue;
    }

    // Dedup op bedrijfsdomein: verrijken i.p.v. dupliceren.
    const company = await db.company.upsert({
      where: { tenantId_domain: { tenantId, domain } },
      create: {
        tenantId,
        name: companyName,
        domain,
        city: (row[mapping.city] || '').trim() || null,
        industry: (row[mapping.industry] || '').trim() || null,
      },
      update: {
        city: (row[mapping.city] || '').trim() || undefined,
        industry: (row[mapping.industry] || '').trim() || undefined,
      },
    });

    // Dedup op e-mail: bestaand record verrijken.
    const known = new Set(Object.values(mapping));
    const custom: Record<string, string> = {};
    for (const [k, v] of Object.entries(row)) {
      if (!known.has(k) && v?.trim()) custom[k] = v.trim();
    }
    const existing = await db.contact.findFirst({ where: { email } });
    if (existing) {
      await db.contact.update({
        where: { id: existing.id },
        data: {
          title: (row[mapping.title] || '').trim() || existing.title,
          customFields: { ...(existing.customFields as object), ...custom },
        },
      });
      report.updated += 1;
    } else {
      await db.contact.create({
        data: {
          tenantId,
          companyId: company.id,
          firstName: (row[mapping.firstName] || '').trim() || '-',
          lastName: (row[mapping.lastName] || '').trim() || '-',
          title: (row[mapping.title] || '').trim() || null,
          email,
          source: 'IMPORT',
          customFields: custom,
        },
      });
      report.imported += 1;
    }
  }

  if (!dryRun) {
    await audit(user.userId, 'contacts_imported', 'Tenant', tenantId, { ...report, errors: report.errors.slice(0, 20) });
    // Validatie-job draait via de worker; hier alvast markeren gebeurt automatisch (UNVERIFIED).
  }
  const params = new URLSearchParams({
    tenantId,
    result: JSON.stringify({ ...report, errors: report.errors.slice(0, 10) }),
    ...(dryRun ? { dry: '1' } : {}),
  });
  redirect(`/beheer/prospects/import?${params.toString()}`);
}

export async function validateNow(formData: FormData) {
  await requireStaff();
  const tenantId = String(formData.get('tenantId'));
  const { validateContacts } = await import('@/jobs/maintenance');
  await validateContacts(tenantId, 500);
  revalidatePath('/beheer/prospects');
}

// ---------- Campagnes (§5) ----------

export async function createCampaign(formData: FormData) {
  const user = await requireStaff();
  const tenantId = String(formData.get('tenantId'));
  const db = tenantDb(tenantId);
  const campaign = await db.campaign.create({
    data: {
      tenantId,
      name: String(formData.get('name') || 'Nieuwe campagne'),
      proposition: String(formData.get('proposition') || '') || null,
      dailyCampaignCap: Number(formData.get('dailyCampaignCap')) || null,
      sendWindowStart: String(formData.get('sendWindowStart') || '08:30'),
      sendWindowEnd: String(formData.get('sendWindowEnd') || '17:00'),
    },
  });
  await audit(user.userId, 'campaign_created', 'Campaign', campaign.id);
  redirect(`/beheer/campagnes/${campaign.id}`);
}

export async function saveStep(formData: FormData) {
  await requireStaff();
  const campaignId = String(formData.get('campaignId'));
  const stepId = String(formData.get('stepId') || '');
  const data = {
    waitDays: Number(formData.get('waitDays')) || 0,
    subjectA: String(formData.get('subjectA') || ''),
    bodyA: String(formData.get('bodyA') || ''),
    subjectB: String(formData.get('subjectB') || '') || null,
    bodyB: String(formData.get('bodyB') || '') || null,
    abSplit: Number(formData.get('abSplit')) || 50,
  };
  if (stepId) {
    await prisma.sequenceStep.update({ where: { id: stepId }, data });
  } else {
    const count = await prisma.sequenceStep.count({ where: { campaignId } });
    await prisma.sequenceStep.create({ data: { ...data, campaignId, order: count } });
  }
  revalidatePath(`/beheer/campagnes/${campaignId}`);
}

export async function deleteStep(formData: FormData) {
  await requireStaff();
  const stepId = String(formData.get('stepId'));
  const step = await prisma.sequenceStep.delete({ where: { id: stepId } });
  revalidatePath(`/beheer/campagnes/${step.campaignId}`);
}

/**
 * Enrollen van de doelgroep (§5/§6): alleen toegestane emailStatus, suppressie-check,
 * round-robin over actieve mailboxen; enrollments starten in PENDING_PERSONALIZATION.
 */
export async function enrollProspects(formData: FormData) {
  const user = await requireStaff();
  const campaignId = String(formData.get('campaignId'));
  const allowRisky = formData.get('allowRisky') === '1';
  const campaign = await prisma.campaign.findUniqueOrThrow({
    where: { id: campaignId },
    include: { tenant: true },
  });
  const db = tenantDb(campaign.tenantId);

  const mailboxes = await prisma.mailbox.findMany({
    where: {
      sendingDomain: { tenantId: campaign.tenantId },
      status: { in: ['ACTIVE', 'WARMING'] },
    },
    select: { id: true },
  });
  if (mailboxes.length === 0) {
    redirect(`/beheer/campagnes/${campaignId}?error=geen-mailboxen`);
  }

  const contacts = await db.contact.findMany({
    where: {
      emailStatus: allowRisky ? { in: ['VALID', 'RISKY'] } : 'VALID',
      enrollments: { none: { campaignId } },
    },
    take: 1000,
  });
  const suppressedSet = await findSuppressed(campaign.tenantId, contacts.map((c) => c.email));
  const eligible = contacts.filter((c) => !suppressedSet.has(c.email.toLowerCase()) && isEnrollable(c.emailStatus, allowRisky));

  const assigned = assignMailboxesRoundRobin(eligible, mailboxes.map((m) => m.id));
  for (const { item: contact, mailboxId } of assigned) {
    const enrollment = await prisma.enrollment.create({
      data: {
        campaignId,
        contactId: contact.id,
        mailboxId,
        variant: Math.random() * 100 < 50 ? 'A' : 'B',
        status: 'PENDING_PERSONALIZATION',
      },
    });
    await prisma.activity.create({
      data: {
        tenantId: campaign.tenantId, contactId: contact.id, campaignId,
        enrollmentId: enrollment.id, type: 'EMAIL_QUEUED', meta: { event: 'enrolled' },
      },
    });
    // Personalisatie direct genereren (in productie via de worker-queue; hier
    // synchroon zodat het ook zonder draaiende worker werkt in demo).
    await generateOpener(enrollment.id);
  }
  await audit(user.userId, 'prospects_enrolled', 'Campaign', campaignId, { count: assigned.length });
  revalidatePath(`/beheer/campagnes/${campaignId}`);
}

/** Activeren kan alleen als aan alle voorwaarden van §5 is voldaan (afgedwongen hier, backend). */
export async function activateCampaign(formData: FormData) {
  const user = await requireStaff();
  const campaignId = String(formData.get('campaignId'));
  const campaign = await prisma.campaign.findUniqueOrThrow({
    where: { id: campaignId },
    include: { sequenceSteps: { orderBy: { order: 'asc' } }, enrollments: { include: { contact: { include: { company: true } } } } },
  });

  const issues = lintSequence(campaign.sequenceSteps);
  if (hasBlockers(issues)) {
    redirect(`/beheer/campagnes/${campaignId}?error=lint`);
  }
  if (campaign.sequenceSteps.length === 0) {
    redirect(`/beheer/campagnes/${campaignId}?error=geen-stappen`);
  }
  // ≥95% van de selectie moet alle variabelen kunnen resolven.
  const sample = campaign.enrollments.slice(0, 200);
  if (sample.length > 0) {
    let okCount = 0;
    for (const e of sample) {
      const vars = buildVars({
        firstName: e.contact.firstName,
        lastName: e.contact.lastName,
        companyName: e.contact.company.name,
        title: e.contact.title,
        city: e.contact.company.city,
        opener: e.personalizedOpener ?? 'x',
        customFields: (e.contact.customFields as Record<string, unknown>) ?? {},
      });
      const allOk = campaign.sequenceSteps.every(
        (s) => renderTemplate(s.subjectA, vars).ok && renderTemplate(s.bodyA, vars).ok,
      );
      if (allOk) okCount += 1;
    }
    if (okCount / sample.length < 0.95) {
      redirect(`/beheer/campagnes/${campaignId}?error=variabelen`);
    }
  }
  const badStatus = campaign.enrollments.some(
    (e) => e.contact.emailStatus !== 'VALID' && e.contact.emailStatus !== 'RISKY',
  );
  if (badStatus) {
    redirect(`/beheer/campagnes/${campaignId}?error=emailstatus`);
  }

  await prisma.campaign.update({ where: { id: campaignId }, data: { status: 'ACTIVE' } });
  await audit(user.userId, 'campaign_activated', 'Campaign', campaignId);
  revalidatePath(`/beheer/campagnes/${campaignId}`);
}

export async function pauseCampaign(formData: FormData) {
  const user = await requireStaff();
  const campaignId = String(formData.get('campaignId'));
  await prisma.campaign.update({ where: { id: campaignId }, data: { status: 'PAUSED' } });
  await audit(user.userId, 'campaign_paused', 'Campaign', campaignId);
  revalidatePath(`/beheer/campagnes/${campaignId}`);
}

// ---------- Reviewflow (§6) ----------

export async function approveOpener(formData: FormData) {
  const user = await requireStaff();
  const enrollmentId = String(formData.get('enrollmentId'));
  const opener = String(formData.get('opener') || '').trim();
  await prisma.enrollment.update({
    where: { id: enrollmentId },
    data: { personalizedOpener: opener, openerApprovedBy: user.userId, status: 'ACTIVE' },
  });
  await audit(user.userId, 'opener_approved', 'Enrollment', enrollmentId);
  revalidatePath('/beheer/review');
}

export async function rejectOpener(formData: FormData) {
  const user = await requireStaff();
  const enrollmentId = String(formData.get('enrollmentId'));
  await prisma.enrollment.update({
    where: { id: enrollmentId },
    data: { personalizedOpener: null, status: 'PENDING_PERSONALIZATION' },
  });
  await generateOpener(enrollmentId); // regenereren
  await audit(user.userId, 'opener_rejected', 'Enrollment', enrollmentId);
  revalidatePath('/beheer/review');
}

export async function bulkApprove(formData: FormData) {
  const user = await requireStaff();
  const campaignId = String(formData.get('campaignId'));
  const pending = await prisma.enrollment.findMany({
    where: { campaignId, status: 'PENDING_APPROVAL' },
    select: { id: true },
  });
  for (const e of pending) {
    await prisma.enrollment.update({
      where: { id: e.id },
      data: { openerApprovedBy: user.userId, status: 'ACTIVE' },
    });
  }
  await audit(user.userId, 'openers_bulk_approved', 'Campaign', campaignId, { count: pending.length });
  revalidatePath('/beheer/review');
}

// ---------- Inbox (§8/§10) ----------

export async function makeLead(formData: FormData) {
  const user = await requireStaff();
  const messageId = String(formData.get('messageId'));
  const message = await prisma.message.findUniqueOrThrow({
    where: { id: messageId },
    include: { enrollment: { include: { contact: true } } },
  });
  if (!message.enrollment) return;
  const lead = await prisma.lead.create({
    data: {
      tenantId: message.tenantId,
      contactId: message.enrollment.contactId,
      campaignId: message.enrollment.campaignId,
      replySnippet: message.body.slice(0, 300),
      viaReferral: message.enrollment.contact.source === 'REFERRAL',
    },
  });
  await prisma.activity.create({
    data: {
      tenantId: message.tenantId, contactId: message.enrollment.contactId,
      campaignId: message.enrollment.campaignId, enrollmentId: message.enrollmentId,
      type: 'LEAD_CREATED', meta: { leadId: lead.id, manual: true },
    },
  });
  await audit(user.userId, 'lead_created_manual', 'Lead', lead.id);
  revalidatePath('/beheer/inbox');
}

export async function reclassify(formData: FormData) {
  const user = await requireStaff();
  const messageId = String(formData.get('messageId'));
  const classification = String(formData.get('classification')) as never;
  await prisma.message.update({
    where: { id: messageId },
    data: { classifiedAs: classification, classificationConfirmed: true },
  });
  await audit(user.userId, 'message_reclassified', 'Message', messageId, { classification });
  revalidatePath('/beheer/inbox');
}

export async function stopEnrollment(formData: FormData) {
  const user = await requireStaff();
  const enrollmentId = String(formData.get('enrollmentId'));
  await prisma.enrollment.update({
    where: { id: enrollmentId },
    data: { status: 'STOPPED', nextSendAt: null },
  });
  await audit(user.userId, 'enrollment_stopped', 'Enrollment', enrollmentId);
  revalidatePath('/beheer/inbox');
}

export async function unsubscribeContact(formData: FormData) {
  const user = await requireStaff();
  const messageId = String(formData.get('messageId'));
  const message = await prisma.message.findUniqueOrThrow({
    where: { id: messageId },
    include: { enrollment: { include: { contact: true } } },
  });
  if (!message.enrollment) return;
  await suppress(message.tenantId, message.enrollment.contact.email, 'UNSUBSCRIBE');
  await audit(user.userId, 'contact_unsubscribed_manual', 'Contact', message.enrollment.contactId);
  revalidatePath('/beheer/inbox');
}

/** Verstuurt een (bewerkt) conceptantwoord als echte thread-reply (§10). */
export async function sendReply(formData: FormData) {
  const user = await requireStaff();
  const draftId = String(formData.get('draftId'));
  const finalBody = String(formData.get('finalBody') || '').trim();
  if (!finalBody) return;

  const draft = await prisma.replyDraft.findUniqueOrThrow({
    where: { id: draftId },
    include: { message: { include: { enrollment: { include: { mailbox: true, contact: true } } } } },
  });
  const inbound = draft.message;
  const enrollment = inbound.enrollment;
  if (!enrollment) return;

  const result = await sendMail(enrollment.mailbox, {
    tenantId: draft.tenantId,
    to: enrollment.contact.email,
    subject: draft.draftSubject,
    bodyText: finalBody,
    senderAddress: '',
    inReplyTo: inbound.messageId,
    references: [inbound.messageId],
    isReply: true, // buiten campagne-caps; geen tracking/afmeldfooter op een lopend gesprek
  });
  if (!result.ok) {
    redirect(`/beheer/inbox?error=verzenden-mislukt`);
  }

  const sent = await prisma.message.create({
    data: {
      enrollmentId: enrollment.id,
      tenantId: draft.tenantId,
      direction: 'OUT',
      messageId: result.messageId,
      inReplyTo: inbound.messageId,
      subject: draft.draftSubject,
      body: finalBody,
      fromEmail: enrollment.mailbox.email,
      toEmail: enrollment.contact.email,
      mailboxEmail: enrollment.mailbox.email,
      sentAt: new Date(),
    },
  });
  await prisma.replyDraft.update({
    where: { id: draftId },
    data: {
      status: 'SENT',
      finalBody,
      sentMessageId: sent.id,
    },
  });
  await prisma.activity.create({
    data: {
      tenantId: draft.tenantId, contactId: enrollment.contactId, campaignId: enrollment.campaignId,
      enrollmentId: enrollment.id, type: 'NOTE', meta: { event: 'reply_sent', draftId },
    },
  });
  await audit(user.userId, 'reply_sent', 'ReplyDraft', draftId);
  revalidatePath('/beheer/inbox');
}

export async function discardDraft(formData: FormData) {
  await requireStaff();
  const draftId = String(formData.get('draftId'));
  await prisma.replyDraft.update({ where: { id: draftId }, data: { status: 'DISCARDED' } });
  revalidatePath('/beheer/inbox');
}

// ---------- Referrals (§9) ----------

export async function updateReferral(formData: FormData) {
  await requireStaff();
  const id = String(formData.get('id'));
  await prisma.referral.update({
    where: { id },
    data: {
      suggestedName: String(formData.get('suggestedName') || '') || null,
      suggestedEmail: String(formData.get('suggestedEmail') || '').toLowerCase() || null,
      suggestedTitle: String(formData.get('suggestedTitle') || '') || null,
      suggestedCompany: String(formData.get('suggestedCompany') || '') || null,
    },
  });
  revalidatePath('/beheer/referrals');
}

export async function rejectReferral(formData: FormData) {
  const user = await requireStaff();
  const id = String(formData.get('id'));
  await prisma.referral.update({ where: { id }, data: { status: 'REJECTED' } });
  await audit(user.userId, 'referral_rejected', 'Referral', id);
  revalidatePath('/beheer/referrals');
}

/**
 * "Maak contact + start opvolging" (§9): nieuw Contact met source=REFERRAL,
 * suppressie-check + validatie, en een concept-referralmail in de reviewflow
 * als losse 1-stapssequence.
 */
export async function approveReferral(formData: FormData) {
  const user = await requireStaff();
  const id = String(formData.get('id'));
  const referral = await prisma.referral.findUniqueOrThrow({ where: { id } });
  if (!referral.suggestedEmail) {
    redirect('/beheer/referrals?error=geen-adres'); // nooit adressen raden
  }
  const email = referral.suggestedEmail.toLowerCase();
  const db = tenantDb(referral.tenantId);

  // Suppressie-check zoals elke andere prospect.
  const suppressedSet = await findSuppressed(referral.tenantId, [email]);
  if (suppressedSet.has(email)) {
    redirect('/beheer/referrals?error=gesupprimeerd');
  }

  const source = await prisma.contact.findFirst({
    where: { id: referral.sourceContactId },
    include: { company: true },
  });
  if (!source) return;

  // Zelfde bedrijf, of nieuw bedrijf als de verwijzing extern is (ander domein).
  const emailDomain = email.split('@')[1];
  let companyId = source.companyId;
  if (referral.suggestedCompany || (emailDomain && emailDomain !== source.company.domain)) {
    const company = await db.company.upsert({
      where: { tenantId_domain: { tenantId: referral.tenantId, domain: emailDomain } },
      create: { tenantId: referral.tenantId, name: referral.suggestedCompany || emailDomain, domain: emailDomain },
      update: {},
    });
    companyId = company.id;
  }

  const [firstName, ...rest] = (referral.suggestedName || 'Onbekend').split(' ');
  const emailStatus = await validateEmail(email);
  const existing = await db.contact.findFirst({ where: { email } });
  const contact =
    existing ??
    (await db.contact.create({
      data: {
        tenantId: referral.tenantId,
        companyId,
        firstName,
        lastName: rest.join(' ') || '-',
        title: referral.suggestedTitle,
        email,
        emailStatus,
        source: 'REFERRAL',
        customFields: { verwijzer_naam: `${source.firstName} ${source.lastName}`, verwijzer_functie: source.title ?? '' },
      },
    }));

  // Losse 1-staps-referralcampagne per tenant (hergebruikt indien aanwezig).
  let campaign = await db.campaign.findFirst({ where: { name: 'Referral-opvolging' } });
  if (!campaign) {
    campaign = await db.campaign.create({
      data: {
        tenantId: referral.tenantId,
        name: 'Referral-opvolging',
        status: 'ACTIVE',
        requiresApproval: true,
      },
    });
    await prisma.sequenceStep.create({
      data: {
        campaignId: campaign.id,
        order: 0,
        waitDays: 0,
        subjectA: 'Doorverwezen door {{verwijzer_naam}}',
        bodyA:
          'Beste {{voornaam}},\n\nIk sprak zojuist met {{verwijzer_naam}}, die gaf aan dat ik hiervoor bij u moet zijn.\n\n{{opener}}\n\nZou een korte kennismaking interessant zijn?\n\nMet vriendelijke groet',
      },
    });
  }

  const mailbox = await prisma.mailbox.findFirst({
    where: { sendingDomain: { tenantId: referral.tenantId }, status: { in: ['ACTIVE', 'WARMING'] } },
  });
  if (!mailbox) {
    redirect('/beheer/referrals?error=geen-mailboxen');
  }

  const enrollment = await prisma.enrollment.create({
    data: {
      campaignId: campaign.id,
      contactId: contact.id,
      mailboxId: mailbox.id,
      status: 'PENDING_PERSONALIZATION',
    },
  });
  await generateOpener(enrollment.id);
  await prisma.referral.update({
    where: { id },
    data: { status: 'CONTACT_CREATED', createdContactId: contact.id },
  });
  await audit(user.userId, 'referral_approved', 'Referral', id, { contactId: contact.id });
  revalidatePath('/beheer/referrals');
}

// ---------- Domeinen & mailboxen (§7a/§7b) ----------

export async function createDomain(formData: FormData) {
  const user = await requireStaff();
  const tenantId = String(formData.get('tenantId'));
  const db = tenantDb(tenantId);
  const domain = await db.sendingDomain.create({
    data: {
      tenantId,
      domain: String(formData.get('domain') || '').toLowerCase().trim(),
      dkimSelector: String(formData.get('dkimSelector') || 'default'),
    },
  });
  await audit(user.userId, 'domain_created', 'SendingDomain', domain.id);
  await dnsCheckOne(domain.id);
  revalidatePath('/beheer/infra');
}

export async function checkDomainNow(formData: FormData) {
  await requireStaff();
  await dnsCheckOne(String(formData.get('domainId')));
  revalidatePath('/beheer/infra');
}

export async function createMailbox(formData: FormData) {
  const user = await requireStaff();
  const mailbox = await prisma.mailbox.create({
    data: {
      sendingDomainId: String(formData.get('sendingDomainId')),
      email: String(formData.get('email') || '').toLowerCase().trim(),
      displayName: String(formData.get('displayName') || ''),
      smtpHost: String(formData.get('smtpHost') || ''),
      smtpPort: Number(formData.get('smtpPort')) || 587,
      smtpUser: String(formData.get('smtpUser') || ''),
      smtpPassEncrypted: encryptSecret(String(formData.get('smtpPass') || '')),
      imapHost: String(formData.get('imapHost') || ''),
      imapPort: Number(formData.get('imapPort')) || 993,
      imapUser: String(formData.get('imapUser') || ''),
      imapPassEncrypted: encryptSecret(String(formData.get('imapPass') || '')),
      status: 'WARMING',
      warmupStartedAt: new Date(),
      warmupDay: 0,
      dailyCap: warmupCapForDay(0),
      maxDailyCap: DEFAULT_MAX_CAP,
    },
  });
  await audit(user.userId, 'mailbox_created', 'Mailbox', mailbox.id);
  revalidatePath('/beheer/infra');
}

/** Cap verhogen boven 50 kan alleen een ADMIN (§7b). */
export async function setMaxCap(formData: FormData) {
  const requested = Number(formData.get('maxDailyCap')) || DEFAULT_MAX_CAP;
  const user = requested > DEFAULT_MAX_CAP ? await requireAdmin() : await requireStaff();
  const mailboxId = String(formData.get('mailboxId'));
  const clamped = clampMaxCap(requested);
  const mb = await prisma.mailbox.findUniqueOrThrow({ where: { id: mailboxId } });
  await prisma.mailbox.update({
    where: { id: mailboxId },
    data: { maxDailyCap: clamped, dailyCap: Math.min(warmupCapForDay(mb.warmupDay, clamped), clamped) },
  });
  await audit(user.userId, 'mailbox_cap_changed', 'Mailbox', mailboxId, { maxDailyCap: clamped });
  revalidatePath('/beheer/infra');
}

// ---------- Abonnementen (§13) ----------

export async function createPlan(formData: FormData) {
  const user = await requireAdmin();
  const plan = await prisma.plan.create({
    data: {
      name: String(formData.get('name') || ''),
      type: formData.get('type') === 'DATA_ONLY' ? 'DATA_ONLY' : 'CAMPAIGN',
      monthlyPriceCents: Math.round(Number(formData.get('monthlyPrice')) * 100) || 0,
      setupFeeCents: Math.round(Number(formData.get('setupFee')) * 100) || 0,
      includedActiveProspects: Number(formData.get('includedActiveProspects')) || 0,
      includedMailboxes: Number(formData.get('includedMailboxes')) || 1,
    },
  });
  await audit(user.userId, 'plan_created', 'Plan', plan.id);
  revalidatePath('/beheer/abonnementen');
}

export async function createSubscription(formData: FormData) {
  const user = await requireAdmin();
  const sub = await prisma.subscription.create({
    data: {
      tenantId: String(formData.get('tenantId')),
      planId: String(formData.get('planId')),
      status: 'ACTIVE',
      priceOverrideCents: formData.get('priceOverride')
        ? Math.round(Number(formData.get('priceOverride')) * 100)
        : null,
    },
  });
  await audit(user.userId, 'subscription_created', 'Subscription', sub.id);
  revalidatePath('/beheer/abonnementen');
}

export async function runDataHealthNow(formData: FormData) {
  const user = await requireStaff();
  const tenantId = String(formData.get('tenantId'));
  const runId = await runDataHealth(tenantId);
  await audit(user.userId, 'datahealth_run', 'DataHealthRun', runId);
  revalidatePath('/beheer/tenants');
}

// ---------- Marktintelligentie & beldata ----------

export async function buildSnapshotNow(formData: FormData) {
  const user = await requireStaff();
  const tenantId = String(formData.get('tenantId'));
  const { buildSnapshot } = await import('@/jobs/insights');
  const prev = new Date();
  prev.setUTCMonth(prev.getUTCMonth() - 1);
  await buildSnapshot(tenantId, prev);
  const id = await buildSnapshot(tenantId, new Date());
  await audit(user.userId, 'insight_snapshot_built', 'InsightSnapshot', id);
  revalidatePath('/beheer/beldata');
  revalidatePath('/portaal/inzichten');
}

/**
 * Belexport-import (Steam Connect/Belstat): koppelt belresultaten aan contacten
 * zodat beldata in dezelfde Activity-tijdlijn en analyses meedraait als e-mail.
 * Kolommen: email OF bedrijf, resultaat, datum (optioneel), notitie (optioneel).
 */
export async function importCallData(formData: FormData) {
  const user = await requireStaff();
  const tenantId = String(formData.get('tenantId'));
  const csv = String(formData.get('csv') || '');
  const parsed = Papa.parse<Record<string, string>>(csv.trim(), { header: true, skipEmptyLines: true });
  const db = tenantDb(tenantId);

  let matched = 0;
  let unmatched = 0;
  for (const row of parsed.data) {
    const email = (row.email || row['e-mail'] || '').trim().toLowerCase();
    const companyName = (row.bedrijf || row.company || '').trim();
    const result = (row.resultaat || row.result || row.resultaatcode || '').trim();
    const note = (row.notitie || row.note || '').trim();
    const when = row.datum ? new Date(row.datum) : new Date();

    let contact = email ? await db.contact.findFirst({ where: { email } }) : null;
    if (!contact && companyName) {
      contact = await db.contact.findFirst({
        where: { company: { name: { contains: companyName, mode: 'insensitive' } } },
      });
    }
    if (!contact) {
      unmatched += 1;
      continue;
    }
    await prisma.activity.create({
      data: {
        tenantId,
        contactId: contact.id,
        type: result ? 'CALL_RESULT' : 'CALL_MADE',
        meta: { resultaat: result || null, notitie: note || null, bron: 'belexport' },
        occurredAt: isNaN(when.getTime()) ? new Date() : when,
      },
    });
    matched += 1;
  }
  await audit(user.userId, 'calldata_imported', 'Tenant', tenantId, { matched, unmatched });
  redirect(`/beheer/beldata?tenantId=${tenantId}&matched=${matched}&unmatched=${unmatched}`);
}

// ---------- Demo-simulatie (acceptatiecriteria §18) ----------

/** Simuleert een inkomende reply op de laatst verzonden mail van een contact (alleen demo-modus). */
export async function simulateReply(formData: FormData) {
  await requireStaff();
  const { getSendMode } = await import('@/lib/env');
  if (getSendMode() !== 'demo') redirect('/beheer/inbox?error=alleen-demo');
  const enrollmentId = String(formData.get('enrollmentId'));
  const body = String(formData.get('body') || '');
  const enrollment = await prisma.enrollment.findUniqueOrThrow({
    where: { id: enrollmentId },
    include: { contact: true, mailbox: true },
  });
  const lastOut = await prisma.message.findFirst({
    where: { enrollmentId, direction: 'OUT' },
    orderBy: { createdAt: 'desc' },
  });
  await processInbound({
    mailboxEmail: enrollment.mailbox.email,
    fromEmail: enrollment.contact.email,
    subject: `Re: ${lastOut?.subject ?? 'uw bericht'}`,
    body,
    messageId: `<sim-${Date.now()}@demo.local>`,
    inReplyTo: lastOut?.messageId,
    receivedAt: new Date(),
  });
  revalidatePath('/beheer/inbox');
}

/** Voert een geplande verzending direct uit (demo-hulpmiddel). */
export async function sendNow(formData: FormData) {
  await requireStaff();
  const enrollmentId = String(formData.get('enrollmentId'));
  await processSend(enrollmentId);
  revalidatePath('/beheer/campagnes');
}
