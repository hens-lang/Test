import { describe, it, expect } from 'vitest';
import { normalizeTemplate, templateHash, isSafeForLibrary, isDisplayable, MIN_SAMPLE_FOR_DISPLAY } from '@/core/anonymize';

describe('template-anonimisering (§12)', () => {
  it('neutraliseert alle variabelen naar placeholders', () => {
    const n = normalizeTemplate('Beste {{voornaam}}, ik zag dat {{bedrijf}} groeit in {{stad}}.');
    expect(n).toBe('Beste {{VAR}}, ik zag dat {{VAR}} groeit in {{VAR}}.');
    expect(n).not.toContain('voornaam');
  });

  it('zelfde template ⇒ zelfde hash, ongeacht whitespace en variabelenamen', () => {
    expect(templateHash('Beste {{voornaam}},\n  hallo')).toBe(templateHash('Beste {{naam}}, hallo'));
  });

  it('weigert teksten met e-mailadressen of URLs (herleidbaar)', () => {
    expect(isSafeForLibrary('Mail mij op jan@bedrijf.nl')).toBe(false);
    expect(isSafeForLibrary('Kijk op https://bedrijf.nl')).toBe(false);
    expect(isSafeForLibrary('Beste {{VAR}}, ik zag dat {{VAR}} groeit.')).toBe(true);
  });

  it('toont statistieken pas vanaf n ≥ 200', () => {
    expect(isDisplayable(MIN_SAMPLE_FOR_DISPLAY - 1)).toBe(false);
    expect(isDisplayable(MIN_SAMPLE_FOR_DISPLAY)).toBe(true);
  });

  it('een genormaliseerd template bevat aantoonbaar geen prospectdata', () => {
    // De aggregatie werkt uitsluitend op TEMPLATES (met {{variabelen}}); na normalisatie
    // resteert alleen door LINK. geschreven tekst met {{VAR}}-placeholders.
    const template = 'Beste {{voornaam}}, {{opener}} Groet, {{verwijzer_naam}}';
    const n = normalizeTemplate(template);
    expect(n.match(/\{\{VAR\}\}/g)?.length).toBe(3);
    expect(isSafeForLibrary(n)).toBe(true);
  });
});
