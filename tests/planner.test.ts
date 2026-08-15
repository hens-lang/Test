import { describe, it, expect } from 'vitest';
import { planSends, isWithinSendWindow, assignMailboxesRoundRobin, MIN_GAP_SECONDS, type MailboxState, type CampaignState } from '@/core/planner';

const mailbox = (over: Partial<MailboxState> = {}): MailboxState => ({
  id: 'mb1', dailyCap: 10, sentToday: 0, status: 'ACTIVE', ...over,
});
const campaign = (over: Partial<CampaignState> = {}): CampaignState => ({
  id: 'c1', status: 'ACTIVE', sendWindowStart: '08:30', sendWindowEnd: '17:00',
  sendDays: '1,2,3,4,5', dailyCampaignCap: null, sentTodayForCampaign: 0, ...over,
});
const enrollments = (n: number, mailboxId = 'mb1', campaignId = 'c1') =>
  Array.from({ length: n }, (_, i) => ({ enrollmentId: `e${i}`, mailboxId, campaignId }));

describe('verzendplanner (§7c)', () => {
  const now = new Date('2026-08-10T09:00:00Z');

  it('overschrijdt nooit de dagcap van een mailbox', () => {
    const planned = planSends(
      enrollments(50),
      new Map([['mb1', mailbox({ dailyCap: 10, sentToday: 4 })]]),
      new Map([['c1', campaign()]]),
      now, 100_000, () => 0.5,
    );
    expect(planned.length).toBe(6); // 10 - 4 al verzonden
  });

  it('overschrijdt nooit de dailyCampaignCap', () => {
    const planned = planSends(
      enrollments(50),
      new Map([['mb1', mailbox({ dailyCap: 100 })]]),
      new Map([['c1', campaign({ dailyCampaignCap: 5 })]]),
      now, 100_000, () => 0.5,
    );
    expect(planned.length).toBe(5);
  });

  it('houdt minimaal 90s tussen mails uit dezelfde mailbox', () => {
    const planned = planSends(
      enrollments(5),
      new Map([['mb1', mailbox()]]),
      new Map([['c1', campaign()]]),
      now, 100_000, () => 0,
    );
    for (let i = 1; i < planned.length; i++) {
      const gap = (planned[i].sendAt.getTime() - planned[i - 1].sendAt.getTime()) / 1000;
      expect(gap).toBeGreaterThanOrEqual(MIN_GAP_SECONDS);
    }
  });

  it('plant niets voor gepauzeerde mailboxen of campagnes', () => {
    expect(planSends(enrollments(5), new Map([['mb1', mailbox({ status: 'PAUSED' })]]), new Map([['c1', campaign()]]), now, 100_000).length).toBe(0);
    expect(planSends(enrollments(5), new Map([['mb1', mailbox()]]), new Map([['c1', campaign({ status: 'PAUSED' })]]), now, 100_000).length).toBe(0);
  });

  it('plant niets buiten het venster van vandaag', () => {
    const planned = planSends(enrollments(5), new Map([['mb1', mailbox()]]), new Map([['c1', campaign()]]), now, 60, () => 0.99);
    expect(planned.length).toBeLessThanOrEqual(1);
  });

  it('verzendvenster respecteert dagen en tijden (Europe/Amsterdam)', () => {
    // Maandag 10 aug 2026, 09:00 UTC = 11:00 Amsterdam
    expect(isWithinSendWindow(new Date('2026-08-10T09:00:00Z'), campaign(), 'Europe/Amsterdam')).toBe(true);
    // Zaterdag
    expect(isWithinSendWindow(new Date('2026-08-15T09:00:00Z'), campaign(), 'Europe/Amsterdam')).toBe(false);
    // Maandag 06:00 UTC = 08:00 Amsterdam → vóór 08:30
    expect(isWithinSendWindow(new Date('2026-08-10T06:00:00Z'), campaign(), 'Europe/Amsterdam')).toBe(false);
    // Maandag 16:00 UTC = 18:00 Amsterdam → na 17:00
    expect(isWithinSendWindow(new Date('2026-08-10T16:00:00Z'), campaign(), 'Europe/Amsterdam')).toBe(false);
  });

  it('verdeelt round-robin over mailboxen', () => {
    const result = assignMailboxesRoundRobin([1, 2, 3, 4, 5], ['a', 'b']);
    expect(result.map((r) => r.mailboxId)).toEqual(['a', 'b', 'a', 'b', 'a']);
  });
});
