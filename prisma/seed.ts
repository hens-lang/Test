// Seed met demodata (§15): 2 tenants, 2 mailboxen (demo), 50 bedrijven/contacten,
// 1 campagne met 3 stappen, gesimuleerde activiteit incl. 1 referral en 1 reply-draft.
import { PrismaClient } from '@prisma/client';
import bcrypt from 'bcryptjs';
import { createCipheriv, randomBytes } from 'crypto';

const prisma = new PrismaClient();

function encrypt(plain: string): string {
  const key = process.env.ENCRYPTION_KEY?.length === 64
    ? Buffer.from(process.env.ENCRYPTION_KEY, 'hex')
    : Buffer.from('00'.repeat(32), 'hex');
  const iv = randomBytes(12);
  const cipher = createCipheriv('aes-256-gcm', key, iv);
  const enc = Buffer.concat([cipher.update(plain, 'utf8'), cipher.final()]);
  return `${iv.toString('base64')}:${cipher.getAuthTag().toString('base64')}:${enc.toString('base64')}`;
}

const VOORNAMEN = ['Jan', 'Piet', 'Kees', 'Marieke', 'Sanne', 'Tom', 'Lisa', 'Bram', 'Eva', 'Daan', 'Femke', 'Ruben', 'Iris', 'Niels', 'Anouk'];
const ACHTERNAMEN = ['Jansen', 'de Vries', 'van den Berg', 'Bakker', 'Visser', 'Smit', 'Meijer', 'Mulder', 'de Boer', 'Dijkstra'];
const FUNCTIES = ['Directeur', 'Operationeel Manager', 'Hoofd Inkoop', 'Commercieel Directeur', 'Office Manager', 'Eigenaar'];
const STEDEN = ['Utrecht', 'Amsterdam', 'Rotterdam', 'Eindhoven', 'Zwolle', 'Groningen', 'Breda'];
const BRANCHES = ['logistiek', 'bouw', 'IT-diensten', 'industrie', 'zakelijke dienstverlening'];

async function main() {
  console.log('Seeden…');

  // Plannen
  const planCampaign = await prisma.plan.create({
    data: {
      name: 'Outreach Pro', type: 'CAMPAIGN', monthlyPriceCents: 149500, setupFeeCents: 75000,
      includedActiveProspects: 500, includedMailboxes: 2, features: { campagnes: true, dashboard: true },
    },
  });
  const planData = await prisma.plan.create({
    data: {
      name: 'Data Fit', type: 'DATA_ONLY', monthlyPriceCents: 49500, setupFeeCents: 25000,
      includedActiveProspects: 2000, includedMailboxes: 0, features: { datahygiene: true },
    },
  });

  // Tenants
  const demo = await prisma.tenant.create({
    data: {
      name: 'Demo Klant', slug: 'demo-klant', industry: 'logistiek', brandColor: '#1d4ed8',
      senderAddress: 'Demo Klant BV, Voorbeeldstraat 1, 3511 AB Utrecht',
      toneOfVoice: 'Professioneel maar toegankelijk. U-vorm. Kort en concreet, geen jargon. Altijd afsluiten met een open vraag.',
      reportRecipients: 'rapportage@demoklant.nl',
    },
  });
  const dataTenant = await prisma.tenant.create({
    data: {
      name: 'Demo Data BV', slug: 'demo-data-bv', industry: 'bouw', brandColor: '#0f766e',
      senderAddress: 'Demo Data BV, Datalaan 2, 5611 CB Eindhoven',
    },
  });
  await prisma.subscription.create({ data: { tenantId: demo.id, planId: planCampaign.id, status: 'ACTIVE' } });
  await prisma.subscription.create({ data: { tenantId: dataTenant.id, planId: planData.id, status: 'ACTIVE' } });

  // Gebruikers
  const hash = await bcrypt.hash('demo1234', 12);
  await prisma.user.createMany({
    data: [
      { email: 'admin@linkgrp.nl', passwordHash: hash, name: 'LINK. Admin', role: 'ADMIN' },
      { email: 'team@linkgrp.nl', passwordHash: hash, name: 'LINK. Teamlid', role: 'MANAGER' },
      { email: 'klant@demoklant.nl', passwordHash: hash, name: 'Demo Klant', role: 'CLIENT', tenantId: demo.id },
      { email: 'klant@demodata.nl', passwordHash: hash, name: 'Demo Data', role: 'CLIENT', tenantId: dataTenant.id },
    ],
  });

  // Verzenddomein + 2 mailboxen (demo-mode: SPF/DKIM als geldig gemarkeerd)
  const domain = await prisma.sendingDomain.create({
    data: {
      tenantId: demo.id, domain: 'mail.demoklant.nl', dkimSelector: 'link',
      spfOk: true, dkimOk: true, dmarcOk: true, mxOk: true, healthScore: 100, status: 'ACTIVE',
      lastCheckedAt: new Date(),
    },
  });
  const mailbox1 = await prisma.mailbox.create({
    data: {
      sendingDomainId: domain.id, email: 'jan@mail.demoklant.nl', displayName: 'Jan van LINK.',
      smtpHost: 'smtp.demo.local', smtpPort: 587, smtpUser: 'jan', smtpPassEncrypted: encrypt('demo'),
      imapHost: 'imap.demo.local', imapPort: 993, imapUser: 'jan', imapPassEncrypted: encrypt('demo'),
      status: 'ACTIVE', dailyCap: 50, maxDailyCap: 50, warmupDay: 28, warmupStartedAt: new Date(Date.now() - 28 * 86400_000),
    },
  });
  await prisma.mailbox.create({
    data: {
      sendingDomainId: domain.id, email: 'sophie@mail.demoklant.nl', displayName: 'Sophie van LINK.',
      smtpHost: 'smtp.demo.local', smtpPort: 587, smtpUser: 'sophie', smtpPassEncrypted: encrypt('demo'),
      imapHost: 'imap.demo.local', imapPort: 993, imapUser: 'sophie', imapPassEncrypted: encrypt('demo'),
      status: 'WARMING', dailyCap: 10, maxDailyCap: 50, warmupDay: 3, warmupStartedAt: new Date(Date.now() - 3 * 86400_000),
    },
  });

  // 50 bedrijven + contacten (verdeeld over beide tenants)
  const contacts: { id: string; tenantId: string }[] = [];
  for (let i = 0; i < 50; i++) {
    const tenant = i < 35 ? demo : dataTenant;
    const cityIdx = i % STEDEN.length;
    const company = await prisma.company.create({
      data: {
        tenantId: tenant.id,
        name: `${ACHTERNAMEN[i % ACHTERNAMEN.length]} ${['Transport', 'Bouw', 'Solutions', 'Groep', 'Techniek'][i % 5]} BV`,
        domain: `bedrijf${i}.nl`,
        industry: BRANCHES[i % BRANCHES.length],
        city: STEDEN[cityIdx],
        websiteSummary: i % 3 === 0 ? `Familiebedrijf in ${BRANCHES[i % BRANCHES.length]}, actief in de regio ${STEDEN[cityIdx]}. Bekend om betrouwbare service en vaste klantrelaties.` : null,
      },
    });
    const contact = await prisma.contact.create({
      data: {
        tenantId: tenant.id,
        companyId: company.id,
        firstName: VOORNAMEN[i % VOORNAMEN.length],
        lastName: ACHTERNAMEN[(i + 3) % ACHTERNAMEN.length],
        title: FUNCTIES[i % FUNCTIES.length],
        email: `contact@bedrijf${i}.nl`,
        emailStatus: i % 10 === 9 ? 'RISKY' : 'VALID',
        emailCheckedAt: new Date(),
        source: 'IMPORT',
      },
    });
    contacts.push({ id: contact.id, tenantId: tenant.id });
  }

  // Campagne met 3 stappen
  const campaign = await prisma.campaign.create({
    data: {
      tenantId: demo.id,
      name: 'Q3 Logistiek Utrecht',
      status: 'ACTIVE',
      proposition: 'Wij leveren gekwalificeerde B2B-afspraken voor logistieke dienstverleners: u schuift alleen nog aan.',
      requiresApproval: true,
    },
  });
  await prisma.sequenceStep.createMany({
    data: [
      {
        campaignId: campaign.id, order: 0, waitDays: 0,
        subjectA: 'Nieuwe klanten voor {{bedrijf}}',
        bodyA: 'Beste {{voornaam}},\n\n{{opener}}\n\nWij vullen agenda’s van logistieke dienstverleners met gekwalificeerde afspraken. Zou dat voor {{bedrijf}} interessant kunnen zijn?\n\nMet vriendelijke groet',
        subjectB: 'Vraag over groei bij {{bedrijf}}',
        bodyB: 'Beste {{voornaam}},\n\n{{opener}}\n\nMag ik u kort bellen om te vertellen hoe wij logistieke bedrijven aan nieuwe klanten helpen?\n\nMet vriendelijke groet',
      },
      {
        campaignId: campaign.id, order: 1, waitDays: 4,
        subjectA: 'Re: Nieuwe klanten voor {{bedrijf}}',
        bodyA: 'Beste {{voornaam}},\n\nIk stuurde u eerder een bericht over nieuwe klanten voor {{bedrijf}}. Wellicht kwam het ongelegen.\n\nZou een korte kennismaking deze of volgende week passen?\n\nMet vriendelijke groet',
      },
      {
        campaignId: campaign.id, order: 2, waitDays: 5,
        subjectA: 'Laatste bericht over {{bedrijf}}',
        bodyA: 'Beste {{voornaam}},\n\nDit is mijn laatste bericht hierover. Mocht nieuwe aanwas later relevant worden, dan hoor ik het graag.\n\nMet vriendelijke groet',
      },
    ],
  });

  // Enrollments + gesimuleerde activiteit
  const demoContacts = contacts.filter((c) => c.tenantId === demo.id).slice(0, 20);
  for (let i = 0; i < demoContacts.length; i++) {
    const c = demoContacts[i];
    const contact = await prisma.contact.findUniqueOrThrow({ where: { id: c.id }, include: { company: true } });
    const opener = `Ik zag dat ${contact.company.name} actief is in ${contact.company.industry} in ${contact.company.city}.`;
    const status = i < 12 ? 'ACTIVE' : i < 16 ? 'PENDING_APPROVAL' : 'PENDING_PERSONALIZATION';
    const enrollment = await prisma.enrollment.create({
      data: {
        campaignId: campaign.id,
        contactId: c.id,
        mailboxId: mailbox1.id,
        variant: i % 2 === 0 ? 'A' : 'B',
        status,
        personalizedOpener: status === 'PENDING_PERSONALIZATION' ? null : opener,
        currentStep: i < 8 ? 1 : 0,
      },
    });
    if (i < 8) {
      // "Verzonden" eerste stap
      const sentAt = new Date(Date.now() - (10 - i) * 86400_000);
      const messageId = `<seed-${i}@mail.demoklant.nl>`;
      await prisma.message.create({
        data: {
          enrollmentId: enrollment.id, tenantId: demo.id, direction: 'OUT', messageId,
          subject: `Nieuwe klanten voor ${contact.company.name}`,
          body: `Beste ${contact.firstName},\n\n${opener}\n\nWij vullen agenda's van logistieke dienstverleners met gekwalificeerde afspraken.\n\nMet vriendelijke groet`,
          fromEmail: 'jan@mail.demoklant.nl', toEmail: contact.email, mailboxEmail: 'jan@mail.demoklant.nl', sentAt,
        },
      });
      await prisma.activity.create({
        data: {
          tenantId: demo.id, contactId: c.id, campaignId: campaign.id, enrollmentId: enrollment.id,
          type: 'EMAIL_SENT', meta: { step: 0, seed: true }, occurredAt: sentAt,
        },
      });
      if (i % 2 === 0) {
        await prisma.activity.create({
          data: {
            tenantId: demo.id, contactId: c.id, campaignId: campaign.id, enrollmentId: enrollment.id,
            type: 'EMAIL_OPENED', meta: { seed: true }, occurredAt: new Date(sentAt.getTime() + 3600_000),
          },
        });
      }
    }
  }

  // 1 positieve reply → lead + reply-draft
  const leadEnrollment = await prisma.enrollment.findFirstOrThrow({
    where: { campaignId: campaign.id, status: 'ACTIVE' },
    include: { contact: { include: { company: true } } },
  });
  const positiveMsg = await prisma.message.create({
    data: {
      enrollmentId: leadEnrollment.id, tenantId: demo.id, direction: 'IN',
      messageId: '<reply-1@bedrijf.nl>', inReplyTo: '<seed-0@mail.demoklant.nl>',
      subject: 'Re: Nieuwe klanten', body: 'Interessant! Kunt u mij volgende week bellen om een afspraak in te plannen?',
      classifiedAs: 'POSITIVE', fromEmail: leadEnrollment.contact.email, mailboxEmail: 'jan@mail.demoklant.nl',
      receivedAt: new Date(Date.now() - 2 * 86400_000),
    },
  });
  await prisma.enrollment.update({ where: { id: leadEnrollment.id }, data: { status: 'REPLIED' } });
  await prisma.activity.createMany({
    data: [
      { tenantId: demo.id, contactId: leadEnrollment.contactId, campaignId: campaign.id, enrollmentId: leadEnrollment.id, type: 'EMAIL_REPLIED', meta: { classification: 'POSITIVE' } },
      { tenantId: demo.id, contactId: leadEnrollment.contactId, campaignId: campaign.id, enrollmentId: leadEnrollment.id, type: 'LEAD_CREATED', meta: { seed: true } },
    ],
  });
  await prisma.lead.create({
    data: {
      tenantId: demo.id, contactId: leadEnrollment.contactId, campaignId: campaign.id,
      replySnippet: 'Interessant! Kunt u mij volgende week bellen om een afspraak in te plannen?', status: 'NEW',
    },
  });
  await prisma.replyDraft.create({
    data: {
      messageId: positiveMsg.id, tenantId: demo.id,
      draftSubject: 'Re: Nieuwe klanten',
      draftBody: 'Dank voor uw reactie, goed om te horen dat het interessant klinkt.\n\nZullen we kort kennismaken? Ik kan bijvoorbeeld dinsdag om 10:00 of donderdag om 14:00.\n\nMet vriendelijke groet',
      generatedBy: 'RULE',
    },
  });

  // 1 referral-reply → suggestie in de werklijst
  const referralEnrollment = await prisma.enrollment.findFirstOrThrow({
    where: { campaignId: campaign.id, status: 'ACTIVE', id: { not: leadEnrollment.id } },
    include: { contact: true },
  });
  const referralMsg = await prisma.message.create({
    data: {
      enrollmentId: referralEnrollment.id, tenantId: demo.id, direction: 'IN',
      messageId: '<reply-2@bedrijf.nl>',
      subject: 'Re: Nieuwe klanten', body: 'Daarvoor moet je bij collega Peter Dijkstra zijn, onze commercieel directeur. Zijn mail is peter.dijkstra@voorbeeldbedrijf.nl.',
      classifiedAs: 'REFERRAL', fromEmail: referralEnrollment.contact.email, mailboxEmail: 'jan@mail.demoklant.nl',
      receivedAt: new Date(Date.now() - 86400_000),
    },
  });
  await prisma.enrollment.update({ where: { id: referralEnrollment.id }, data: { status: 'REPLIED' } });
  await prisma.referral.create({
    data: {
      tenantId: demo.id, sourceContactId: referralEnrollment.contactId, sourceMessageId: referralMsg.id,
      suggestedName: 'Peter Dijkstra', suggestedEmail: 'peter.dijkstra@voorbeeldbedrijf.nl',
      suggestedTitle: 'Commercieel directeur',
      rawSnippet: 'Daarvoor moet je bij collega Peter Dijkstra zijn, onze commercieel directeur. Zijn mail is peter.dijkstra@voorbeeldbedrijf.nl.',
    },
  });
  await prisma.activity.create({
    data: {
      tenantId: demo.id, contactId: referralEnrollment.contactId, campaignId: campaign.id,
      enrollmentId: referralEnrollment.id, type: 'REFERRAL_RECEIVED', meta: { seed: true },
    },
  });

  // DataHealthRun voor de DATA_ONLY-tenant
  await prisma.dataHealthRun.create({
    data: {
      tenantId: dataTenant.id, contactsChecked: 15, newInvalid: 1, newRisky: 2, bouncesRemoved: 0,
      suppressed: 0, enriched: 3,
      reportJson: { samenvatting: 'Gecontroleerd: 15 contacten. Nieuw ongeldig: 1. Nieuw risicovol: 2. Verrijkt: 3.' },
    },
  });

  // TemplateStat-voorbeelddata (geanonimiseerd, boven de toondrempel)
  await prisma.templateStat.createMany({
    data: [
      { industry: 'logistiek', kind: 'SUBJECT', textHash: 'seed-hash-1', textSample: 'Nieuwe klanten voor {{VAR}}', sentCount: 420, replyCount: 38, positiveCount: 12 },
      { industry: 'logistiek', kind: 'SUBJECT', textHash: 'seed-hash-2', textSample: 'Vraag over groei bij {{VAR}}', sentCount: 380, replyCount: 26, positiveCount: 8 },
      { industry: 'logistiek', kind: 'OPENER', textHash: 'seed-hash-3', textSample: 'Ik zag dat {{VAR}} actief is in {{VAR}} in {{VAR}}.', sentCount: 800, replyCount: 61, positiveCount: 19 },
    ],
  });

  console.log('Seed klaar.');
  console.log('Logins (wachtwoord: demo1234):');
  console.log('  admin@linkgrp.nl   (ADMIN)');
  console.log('  team@linkgrp.nl    (MANAGER)');
  console.log('  klant@demoklant.nl (CLIENT, campagne-plan)');
  console.log('  klant@demodata.nl  (CLIENT, data-abonnement)');
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(() => prisma.$disconnect());
