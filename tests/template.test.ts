import { describe, it, expect } from 'vitest';
import { renderTemplate, buildVars, extractVariables } from '@/core/template';

describe('template-rendering (§5)', () => {
  it('rendert variabelen', () => {
    const r = renderTemplate('Beste {{voornaam}} van {{bedrijf}}', { voornaam: 'Jan', bedrijf: 'Acme' });
    expect(r.ok).toBe(true);
    expect(r.text).toBe('Beste Jan van Acme');
  });

  it('blokkeert bij ontbrekende variabelen — nooit "Beste {{voornaam}}" versturen', () => {
    const r = renderTemplate('Beste {{voornaam}}', {});
    expect(r.ok).toBe(false);
    expect(r.missing).toEqual(['voornaam']);
  });

  it('lege strings tellen als ontbrekend', () => {
    expect(renderTemplate('{{stad}}', { stad: '  ' }).ok).toBe(false);
  });

  it('is een safe engine: geen expressies, alleen substitutie', () => {
    const r = renderTemplate('{{constructor}} {{__proto__}}', { constructor: 'x', __proto__: 'y' } as never);
    expect(r.text).toContain('x');
  });

  it('buildVars levert NL-variabelen incl. customFields en verwijzer', () => {
    const vars = buildVars({
      firstName: 'Jan', lastName: 'Jansen', companyName: 'Acme', title: 'CEO', city: 'Utrecht',
      opener: 'Mooi bedrijf.', customFields: { sector: 'bouw' },
      referrerName: 'Piet', referrerTitle: 'CTO',
    });
    expect(vars.voornaam).toBe('Jan');
    expect(vars.bedrijf).toBe('Acme');
    expect(vars.opener).toBe('Mooi bedrijf.');
    expect(vars.sector).toBe('bouw');
    expect(vars.verwijzer_naam).toBe('Piet');
  });

  it('extraheert variabelen uit templates', () => {
    expect(extractVariables('{{a}} en {{ b }} en {{a}}')).toEqual(['a', 'b']);
  });
});
