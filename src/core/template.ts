// Veilige template-rendering met {{variabele}}-syntax.
// Geen eval, geen expressies — alleen platte substitutie.
// Ontbrekende variabelen blokkeren verzending (nooit "Beste {{voornaam}}" versturen).

export interface RenderResult {
  ok: boolean;
  text: string;
  missing: string[];
}

const VAR_RE = /\{\{\s*([a-zA-Z0-9_]+)\s*\}\}/g;

export function extractVariables(template: string): string[] {
  const vars = new Set<string>();
  for (const m of template.matchAll(VAR_RE)) vars.add(m[1]);
  return [...vars];
}

export function renderTemplate(template: string, vars: Record<string, string | undefined | null>): RenderResult {
  const missing: string[] = [];
  const text = template.replace(VAR_RE, (_, name: string) => {
    const v = vars[name];
    if (v === undefined || v === null || String(v).trim() === '') {
      if (!missing.includes(name)) missing.push(name);
      return `{{${name}}}`;
    }
    return String(v);
  });
  return { ok: missing.length === 0, text, missing };
}

export interface ContactVars {
  firstName: string;
  lastName: string;
  companyName: string;
  title?: string | null;
  city?: string | null;
  opener?: string | null;
  customFields?: Record<string, unknown>;
  referrerName?: string | null;
  referrerTitle?: string | null;
}

/** Bouwt de variabelen-map voor een contact (NL variabelenamen conform spec §5/§9). */
export function buildVars(c: ContactVars): Record<string, string | undefined> {
  const custom: Record<string, string> = {};
  for (const [k, v] of Object.entries(c.customFields ?? {})) {
    if (v !== null && v !== undefined) custom[k] = String(v);
  }
  return {
    ...custom,
    voornaam: c.firstName,
    achternaam: c.lastName,
    bedrijf: c.companyName,
    functie: c.title ?? undefined,
    stad: c.city ?? undefined,
    opener: c.opener ?? undefined,
    verwijzer_naam: c.referrerName ?? undefined,
    verwijzer_functie: c.referrerTitle ?? undefined,
  };
}
