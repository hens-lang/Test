import { describe, it, expect } from 'vitest';
import { checkCampaignBounceRate, checkMailboxHealth, checkDomainComplaints, canSend, type SendGateInput } from '@/core/guardrails';

const gateInput = (over: Partial<SendGateInput> = {}): SendGateInput => ({
  domainStatus: 'ACTIVE', domainSpfOk: true, domainDkimOk: true,
  mailboxStatus: 'ACTIVE', mailboxSentToday: 0, mailboxDailyCap: 50,
  campaignStatus: 'ACTIVE', enrollmentStatus: 'ACTIVE',
  suppressed: false, emailStatus: 'VALID', hasUnsubscribeLink: true, ...over,
});

describe('guardrails (§7d)', () => {
  it('pauzeert campagne bij bounce-rate > 3% over de laatste 100', () => {
    expect(checkCampaignBounceRate(100, 4).pause).toBe(true);
    expect(checkCampaignBounceRate(100, 3).pause).toBe(false);
    expect(checkCampaignBounceRate(50, 10).pause).toBe(false); // te weinig volume
  });

  it('pauzeert mailbox bij >5% bounces of 3 SMTP-fouten op rij', () => {
    expect(checkMailboxHealth({ sentToday: 40, bouncedToday: 3, consecutiveSmtpErrors: 0 }).pause).toBe(true);
    expect(checkMailboxHealth({ sentToday: 40, bouncedToday: 1, consecutiveSmtpErrors: 0 }).pause).toBe(false);
    expect(checkMailboxHealth({ sentToday: 5, bouncedToday: 0, consecutiveSmtpErrors: 3 }).pause).toBe(true);
    expect(checkMailboxHealth({ sentToday: 5, bouncedToday: 0, consecutiveSmtpErrors: 2 }).pause).toBe(false);
  });

  it('pauzeert domein bij ≥2 klachten', () => {
    expect(checkDomainComplaints(2).pause).toBe(true);
    expect(checkDomainComplaints(1).pause).toBe(false);
  });
});

describe('harde verzendpoort (§18)', () => {
  it('staat een gezonde verzending toe', () => {
    expect(canSend(gateInput()).allowed).toBe(true);
  });

  it('blokkeert zonder geldige SPF+DKIM — altijd', () => {
    expect(canSend(gateInput({ domainSpfOk: false })).allowed).toBe(false);
    expect(canSend(gateInput({ domainDkimOk: false })).allowed).toBe(false);
  });

  it('blokkeert boven de dagcap van de mailbox', () => {
    expect(canSend(gateInput({ mailboxSentToday: 50, mailboxDailyCap: 50 })).allowed).toBe(false);
  });

  it('blokkeert gesupprimeerde adressen', () => {
    expect(canSend(gateInput({ suppressed: true })).allowed).toBe(false);
  });

  it('blokkeert zonder afmeldlink', () => {
    expect(canSend(gateInput({ hasUnsubscribeLink: false })).allowed).toBe(false);
  });

  it('blokkeert als domein/mailbox/campagne niet actief is', () => {
    expect(canSend(gateInput({ domainStatus: 'PAUSED' })).allowed).toBe(false);
    expect(canSend(gateInput({ mailboxStatus: 'PAUSED' })).allowed).toBe(false);
    expect(canSend(gateInput({ campaignStatus: 'PAUSED' })).allowed).toBe(false);
    expect(canSend(gateInput({ campaignStatus: 'DRAFT' })).allowed).toBe(false);
  });

  it('blokkeert ongeldige e-mailstatussen', () => {
    for (const status of ['INVALID', 'BOUNCED', 'UNSUBSCRIBED', 'UNVERIFIED']) {
      expect(canSend(gateInput({ emailStatus: status })).allowed).toBe(false);
    }
    expect(canSend(gateInput({ emailStatus: 'RISKY' })).allowed).toBe(true);
  });
});
