import { describe, it, expect } from 'vitest';
import { isSuppressedByEntries } from '@/core/suppression';
import { isEnrollable } from '@/core/validation';

describe('suppressie-checks (§4/§7d)', () => {
  const entries = [
    { email: 'globaal@voorbeeld.nl', tenantId: null },
    { email: 'tenant@voorbeeld.nl', tenantId: 'tenant-a' },
  ];

  it('globale suppressie geldt voor elke tenant', () => {
    expect(isSuppressedByEntries('globaal@voorbeeld.nl', entries, 'tenant-a')).toBe(true);
    expect(isSuppressedByEntries('globaal@voorbeeld.nl', entries, 'tenant-b')).toBe(true);
  });

  it('tenant-suppressie geldt alleen voor die tenant', () => {
    expect(isSuppressedByEntries('tenant@voorbeeld.nl', entries, 'tenant-a')).toBe(true);
    expect(isSuppressedByEntries('tenant@voorbeeld.nl', entries, 'tenant-b')).toBe(false);
  });

  it('niet-gesupprimeerde adressen zijn vrij', () => {
    expect(isSuppressedByEntries('vrij@voorbeeld.nl', entries, 'tenant-a')).toBe(false);
  });
});

describe('enrollment-toelating (§4)', () => {
  it('alleen VALID mag standaard een campagne in', () => {
    expect(isEnrollable('VALID', false)).toBe(true);
    expect(isEnrollable('RISKY', false)).toBe(false);
  });
  it('RISKY alleen na expliciete keuze', () => {
    expect(isEnrollable('RISKY', true)).toBe(true);
  });
  it('INVALID/BOUNCED/UNSUBSCRIBED nooit', () => {
    for (const s of ['INVALID', 'BOUNCED', 'UNSUBSCRIBED', 'UNVERIFIED'] as const) {
      expect(isEnrollable(s, true)).toBe(false);
    }
  });
});
