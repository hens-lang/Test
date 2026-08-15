import { describe, it, expect } from 'vitest';
import { extractReferralHeuristic } from '@/core/referral-extract';

describe('referral-extractie fallback (§9)', () => {
  it('haalt naam en e-mail uit een NL-doorverwijzing', () => {
    const r = extractReferralHeuristic(
      'Daarvoor moet je bij collega Peter Dijkstra zijn. Zijn mail is peter.dijkstra@bedrijf.nl.',
      'afzender@bedrijf.nl',
    );
    expect(r.suggestedName).toBe('Peter Dijkstra');
    expect(r.suggestedEmail).toBe('peter.dijkstra@bedrijf.nl');
    expect(r.rawSnippet.length).toBeGreaterThan(0);
  });

  it('negeert het adres van de afzender zelf', () => {
    const r = extractReferralHeuristic('Vraag het even aan afzender@bedrijf.nl of aan collega Jan Bakker.', 'afzender@bedrijf.nl');
    expect(r.suggestedEmail).toBeNull();
    expect(r.suggestedName).toBe('Jan Bakker');
  });

  it('raadt NOOIT een adres als er geen genoemd is', () => {
    const r = extractReferralHeuristic('Hiervoor kun je bij Marie Willems terecht, zij is verantwoordelijk voor inkoop.');
    expect(r.suggestedName).toContain('Marie');
    expect(r.suggestedEmail).toBeNull();
  });

  it('herkent tussenvoegsels', () => {
    const r = extractReferralHeuristic('Daarvoor moet je bij collega Kees van Dam zijn.');
    expect(r.suggestedName).toBe('Kees van Dam');
  });
});
