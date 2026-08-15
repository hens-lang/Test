// Template-anonimisering voor TemplateStat (§12).
// Er komen NOOIT klantnamen, prospectgegevens of herleidbare inhoud in de
// bibliotheek — alleen de templatetekst zoals LINK. die schreef, met alle
// variabelen geneutraliseerd naar placeholders.
import { createHash } from 'crypto';

const KNOWN_VARS = ['voornaam', 'achternaam', 'bedrijf', 'functie', 'stad', 'opener', 'verwijzer_naam', 'verwijzer_functie'];

/**
 * Normaliseert een template: elke {{variabele}} wordt {{VAR}}, whitespace genormaliseerd.
 * Het resultaat bevat per definitie geen ingevulde prospectdata — deze functie werkt
 * op de TEMPLATE (met variabelen), nooit op een gerenderde mail.
 */
export function normalizeTemplate(template: string): string {
  return template
    .replace(/\{\{\s*[a-zA-Z0-9_]+\s*\}\}/g, '{{VAR}}')
    .replace(/\s+/g, ' ')
    .trim();
}

export function templateHash(template: string): string {
  return createHash('sha256').update(normalizeTemplate(template)).digest('hex').slice(0, 32);
}

/**
 * Controle die aggregatie weigert als een tekst er tóch uitziet als gerenderde
 * inhoud i.p.v. een template: e-mailadressen of ingevulde restanten zijn verdacht.
 * Vangnet bovenop het feit dat we alleen templates aanleveren.
 */
export function isSafeForLibrary(templateSample: string): boolean {
  if (/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/.test(templateSample)) return false;
  if (/https?:\/\//.test(templateSample)) return false;
  return true;
}

/** Minimale steekproef voordat statistieken getoond worden (niet herleidbaar naar één klant). */
export const MIN_SAMPLE_FOR_DISPLAY = 200;

export function isDisplayable(sentCount: number): boolean {
  return sentCount >= MIN_SAMPLE_FOR_DISPLAY;
}

export { KNOWN_VARS };
