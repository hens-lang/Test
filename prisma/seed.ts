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
        size: ['1-10', '10-50', '50-100', '100+'][i % 4],
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

  // Bezwaar-replies (NEGATIVE/NOT_NOW) + belactiviteiten voor de inzichtenlaag
  const objectionEnrollments = await prisma.enrollment.findMany({
    where: { campaignId: campaign.id, status: 'ACTIVE' },
    include: { contact: true },
    take: 3,
  });
  const objectionBodies = [
    { c: 'NEGATIVE' as const, body: 'Bedankt, maar we zijn al voorzien — we werken al jaren met een vaste leverancier voor onze leadgeneratie.' },
    { c: 'NOT_NOW' as const, body: 'Interessant, maar niet op dit moment. Ons budget is bevroren tot Q1, kom dan gerust terug.' },
    { c: 'NEGATIVE' as const, body: 'Wij doen dit zelf met een eigen team, dus geen behoefte aan externe partijen.' },
  ];
  for (let i = 0; i < objectionEnrollments.length && i < objectionBodies.length; i++) {
    const e = objectionEnrollments[i];
    await prisma.message.create({
      data: {
        enrollmentId: e.id, tenantId: demo.id, direction: 'IN',
        messageId: `<objection-${i}@bedrijf.nl>`, subject: 'Re: Nieuwe klanten',
        body: objectionBodies[i].body, classifiedAs: objectionBodies[i].c,
        fromEmail: e.contact.email, mailboxEmail: 'jan@mail.demoklant.nl',
        receivedAt: new Date(Date.now() - (3 + i) * 86400_000),
      },
    });
    await prisma.enrollment.update({ where: { id: e.id }, data: { status: 'REPLIED' } });
    await prisma.activity.create({
      data: {
        tenantId: demo.id, contactId: e.contactId, campaignId: campaign.id, enrollmentId: e.id,
        type: 'EMAIL_REPLIED', meta: { classification: objectionBodies[i].c },
        occurredAt: new Date(Date.now() - (3 + i) * 86400_000),
      },
    });
    await prisma.activity.create({
      data: {
        tenantId: demo.id, contactId: e.contactId, type: 'CALL_RESULT',
        meta: { resultaat: ['Afspraak', 'Terugbellen', 'Geen gehoor'][i], bron: 'belexport' },
        occurredAt: new Date(Date.now() - (2 + i) * 86400_000),
      },
    });
  }

  // Drie maand-snapshots (marktintelligentie) zodat inzichten én trends direct tonen
  const now = new Date();
  const periods = [2, 1, 0].map((back) => {
    const d = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth() - back, 1));
    return d.toISOString().slice(0, 7);
  });
  const snapshotSeries = [
    { sent: 180, replies: 7, leads: 1, calls: 40, alVoorzien: 45, budget: 10, timing: 25 },
    { sent: 210, replies: 10, leads: 2, calls: 55, alVoorzien: 38, budget: 18, timing: 26 },
    { sent: 240, replies: 14, leads: 3, calls: 60, alVoorzien: 30, budget: 32, timing: 22 },
  ];
  for (let i = 0; i < 3; i++) {
    const s = snapshotSeries[i];
    await prisma.insightSnapshot.create({
      data: {
        tenantId: demo.id,
        period: periods[i],
        volumeSent: s.sent, volumeReplies: s.replies, volumeLeads: s.leads, volumeCalls: s.calls,
        segmentStats: [
          { dimension: 'branche', value: 'logistiek', sent: Math.round(s.sent * 0.5), replies: Math.round(s.replies * 0.7), leads: s.leads, replyRate: (s.replies * 0.7) / (s.sent * 0.5) },
          { dimension: 'branche', value: 'bouw', sent: Math.round(s.sent * 0.3), replies: Math.round(s.replies * 0.2), leads: 0, replyRate: (s.replies * 0.2) / (s.sent * 0.3) },
          { dimension: 'functiegroep', value: 'Operationeel', sent: Math.round(s.sent * 0.4), replies: Math.round(s.replies * 0.6), leads: s.leads, replyRate: (s.replies * 0.6) / (s.sent * 0.4) },
          { dimension: 'functiegroep', value: 'Directie', sent: Math.round(s.sent * 0.4), replies: Math.round(s.replies * 0.25), leads: 0, replyRate: (s.replies * 0.25) / (s.sent * 0.4) },
          { dimension: 'grootte', value: '10-50', sent: Math.round(s.sent * 0.45), replies: Math.round(s.replies * 0.6), leads: s.leads, replyRate: (s.replies * 0.6) / (s.sent * 0.45) },
          { dimension: 'grootte', value: '100+', sent: Math.round(s.sent * 0.25), replies: Math.round(s.replies * 0.15), leads: 0, replyRate: (s.replies * 0.15) / (s.sent * 0.25) },
          { dimension: 'regio', value: 'Utrecht', sent: Math.round(s.sent * 0.35), replies: Math.round(s.replies * 0.45), leads: s.leads, replyRate: (s.replies * 0.45) / (s.sent * 0.35) },
          { dimension: 'regio', value: 'Rotterdam', sent: Math.round(s.sent * 0.3), replies: Math.round(s.replies * 0.3), leads: 0, replyRate: (s.replies * 0.3) / (s.sent * 0.3) },
        ],
        classificationStats: { POSITIVE: s.leads + 1, NOT_NOW: 4, NEGATIVE: 5, REFERRAL: 1, OOO: 2 },
        objectionClusters: [
          { cluster: 'AL_VOORZIEN', label: 'Al voorzien / vaste leverancier', count: Math.round(s.alVoorzien / 10), share: s.alVoorzien / 100, quotes: ['We werken al jaren met een vaste leverancier voor onze leadgeneratie.'], advice: 'Benoem in de eerste mail expliciet waarin het aanbod verschilt van een zittende leverancier, en vraag naar het contractmoment.' },
          { cluster: 'GEEN_BUDGET', label: 'Geen budget / te duur', count: Math.round(s.budget / 10), share: s.budget / 100, quotes: ['Ons budget is bevroren tot Q1, kom dan gerust terug.'], advice: 'Verschuif de boodschap van kosten naar opbrengst/risico, of richt op segmenten met investeringsruimte.' },
          { cluster: 'SLECHTE_TIMING', label: 'Timing — nu niet, later wel', count: Math.round(s.timing / 10), share: s.timing / 100, quotes: ['Kom in het nieuwe kwartaal maar eens terug.'], advice: 'Zet deze prospects in de heractiveringswachtrij — deze groep komt terug en is dan warm.' },
        ],
        timingStats: { '1': 2, '2': Math.round(s.replies * 0.4), '3': Math.round(s.replies * 0.25), '4': Math.round(s.replies * 0.2), '5': 1 },
        conclusions: [
          `Binnen functiegroep reageert "Operationeel" het best (${((s.replies * 0.6) / (s.sent * 0.4) * 100).toFixed(1)}% reply-rate) — 2,4× beter dan "Directie". Advies: verschuif volume naar operationeel management.`,
          `Het meest gehoorde bezwaar is "${s.budget > s.alVoorzien ? 'Geen budget / te duur' : 'Al voorzien / vaste leverancier'}" (${Math.max(s.budget, s.alVoorzien)}% van de afwijzingen). ${s.budget > s.alVoorzien ? 'Verschuif de boodschap van kosten naar opbrengst — dit signaal wordt sterker en wijst op krappere budgetten in de markt.' : 'Vraag naar het contractmoment en benoem het onderscheid met de zittende leverancier.'}`,
          'De meeste reacties komen op dinsdag binnen — plan belangrijke verzendingen aan het begin van de week.',
          '4 prospects zeiden "nu niet" — deze groep is warm en hoort in de heractiveringswachtrij.',
        ],
      },
    });
  }

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
