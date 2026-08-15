import { describe, it, expect } from 'vitest';
import { classifyReplyHeuristic, isHardBounce, stopsEnrollment } from '@/core/classify';
import { classifyEmail } from '@/core/validation';
import { encryptSecret, decryptSecret } from '@/lib/crypto';
import { makeUnsubscribeToken, verifyUnsubscribeToken } from '@/core/unsubscribe';

describe('reply-classificatie heuristiek (§8)', () => {
  it('herkent de hoofdcategorieën', () => {
    expect(classifyReplyHeuristic('Re: x', 'Interessant! Plan maar een afspraak in.')).toBe('POSITIVE');
    expect(classifyReplyHeuristic('Re: x', 'Daarvoor moet je bij collega Piet zijn.')).toBe('REFERRAL');
    expect(classifyReplyHeuristic('Re: x', 'Niet op dit moment, kom er later op terug.')).toBe('NOT_NOW');
    expect(classifyReplyHeuristic('Re: x', 'Geen interesse.')).toBe('NEGATIVE');
    expect(classifyReplyHeuristic('Automatisch antwoord', 'Ik ben afwezig tot 20 augustus.')).toBe('OOO');
    expect(classifyReplyHeuristic('Re: x', 'Graag afmelden voor deze mails.')).toBe('UNSUBSCRIBE');
    expect(classifyReplyHeuristic('Delivery Status Notification', 'user unknown')).toBe('BOUNCE');
  });
  it('OOO stopt de enrollment niet, de rest wel', () => {
    expect(stopsEnrollment('OOO')).toBe(false);
    expect(stopsEnrollment('POSITIVE')).toBe(true);
    expect(stopsEnrollment('NEGATIVE')).toBe(true);
  });
  it('onderscheidt harde bounces', () => {
    expect(isHardBounce('550 5.1.1 user unknown')).toBe(true);
    expect(isHardBounce('mailbox tijdelijk vol, probeer later')).toBe(false);
  });
});

describe('e-mailvalidatie (§4)', () => {
  it('classificeert syntax, rolgebaseerd en wegwerp', () => {
    expect(classifyEmail('geen-adres', true)).toBe('INVALID');
    expect(classifyEmail('info@bedrijf.nl', true)).toBe('RISKY');
    expect(classifyEmail('jan@mailinator.com', true)).toBe('INVALID');
    expect(classifyEmail('jan@bedrijf.nl', false)).toBe('INVALID'); // geen MX
    expect(classifyEmail('jan@bedrijf.nl', true)).toBe('VALID');
  });
});

describe('credential-versleuteling (§3)', () => {
  it('AES-256-GCM round-trip', () => {
    const key = Buffer.from('11'.repeat(32), 'hex');
    const enc = encryptSecret('supergeheim-wachtwoord', key);
    expect(enc).not.toContain('supergeheim');
    expect(decryptSecret(enc, key)).toBe('supergeheim-wachtwoord');
  });
  it('manipulatie van ciphertext faalt', () => {
    const key = Buffer.from('11'.repeat(32), 'hex');
    const enc = encryptSecret('geheim', key);
    const [iv, tag, data] = enc.split(':');
    const tampered = `${iv}:${tag}:${Buffer.from('aangepast').toString('base64')}`;
    expect(() => decryptSecret(tampered, key)).toThrow();
  });
});

describe('unsubscribe-tokens (§7d)', () => {
  it('round-trip en manipulatiebestendig', () => {
    const token = makeUnsubscribeToken('tenant-1', 'Jan@Bedrijf.nl');
    const data = verifyUnsubscribeToken(token);
    expect(data).toEqual({ tenantId: 'tenant-1', email: 'jan@bedrijf.nl' });
    expect(verifyUnsubscribeToken(token.slice(0, -3) + 'abc')).toBeNull();
    expect(verifyUnsubscribeToken('onzin')).toBeNull();
  });
});
