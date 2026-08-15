import { describe, it, expect } from 'vitest';
import { warmupCapForDay, advanceWarmup, isWarmupComplete, clampMaxCap, ABSOLUTE_MAX_CAP } from '@/core/warmup';

describe('warm-up-schema (§7b)', () => {
  it('volgt het schema 10/20/35/50 per week', () => {
    expect(warmupCapForDay(0)).toBe(10);
    expect(warmupCapForDay(6)).toBe(10);
    expect(warmupCapForDay(7)).toBe(20);
    expect(warmupCapForDay(14)).toBe(35);
    expect(warmupCapForDay(21)).toBe(50);
    expect(warmupCapForDay(100)).toBe(50);
  });

  it('respecteert de maxDailyCap van de mailbox', () => {
    expect(warmupCapForDay(21, 30)).toBe(30);
    expect(warmupCapForDay(0, 5)).toBe(5);
  });

  it('absolute bovengrens is 100, wat er ook gevraagd wordt', () => {
    expect(clampMaxCap(500)).toBe(ABSOLUTE_MAX_CAP);
    expect(clampMaxCap(0)).toBe(1);
  });

  it('warm-up is voltooid na 4 weken', () => {
    expect(isWarmupComplete(27)).toBe(false);
    expect(isWarmupComplete(28)).toBe(true);
  });

  it('advanceWarmup verhoogt dag en herberekent cap', () => {
    const r = advanceWarmup({ warmupDay: 6, maxDailyCap: 50 });
    expect(r.warmupDay).toBe(7);
    expect(r.dailyCap).toBe(20);
    expect(r.completed).toBe(false);
  });
});
