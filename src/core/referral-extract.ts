// Referral-extractie (§9), regelgebaseerde fallback: regex op e-mailadressen +
// naamdetectie na trefwoorden. Nooit adressen raden of genereren — alleen wat
// letterlijk in de tekst staat.

export interface ReferralExtraction {
  suggestedName: string | null;
  suggestedEmail: string | null;
  suggestedTitle: string | null;
  suggestedCompany: string | null;
  rawSnippet: string;
}

const EMAIL_IN_TEXT_RE = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g;

// Naam na trefwoorden: "collega Jan Jansen", "kun je bij Piet de Vries terecht",
// "daarvoor is Marie Willems verantwoordelijk".
const NAME_PATTERNS = [
  /collega\s+([A-Z][a-zà-ÿ]+(?:\s+(?:van|de|der|den|ten|ter|te|van der|van den|van de))?\s*[A-Z][a-zà-ÿ]+)/,
  /(?:kun|kan) je (?:beter )?bij\s+([A-Z][a-zà-ÿ]+(?:\s+(?:van|de|der|den|ten|ter|te))?\s*[A-Z][a-zà-ÿ]+)/,
  /moet je bij\s+([A-Z][a-zà-ÿ]+(?:\s+(?:van|de|der|den|ten|ter|te))?\s*[A-Z][a-zà-ÿ]+)/,
  /(?:daarvoor is|hiervoor is)\s+([A-Z][a-zà-ÿ]+(?:\s+(?:van|de|der|den|ten|ter|te))?\s*[A-Z][a-zà-ÿ]+)/,
  /neem contact op met\s+([A-Z][a-zà-ÿ]+(?:\s+(?:van|de|der|den|ten|ter|te))?\s*[A-Z][a-zà-ÿ]+)/,
  /verantwoordelijk(?:e)? (?:voor .{0,40})?is\s+([A-Z][a-zà-ÿ]+\s+[A-Z][a-zà-ÿ]+)/,
];

const TITLE_PATTERNS = [
  /(?:onze|de)\s+([a-zà-ÿ]+(?:manager|directeur|specialist|adviseur|co[oö]rdinator))/i,
  /\b(hoofd\s+[a-zà-ÿ]+)/i,
];

export function extractReferralHeuristic(replyBody: string, replierEmail?: string): ReferralExtraction {
  const emails = [...replyBody.matchAll(EMAIL_IN_TEXT_RE)]
    .map((m) => m[0].toLowerCase())
    .filter((e) => e !== replierEmail?.toLowerCase());
  let name: string | null = null;
  for (const p of NAME_PATTERNS) {
    const m = replyBody.match(p);
    if (m) {
      name = m[1].trim();
      break;
    }
  }
  let title: string | null = null;
  for (const p of TITLE_PATTERNS) {
    const m = replyBody.match(p);
    if (m) {
      title = m[1].trim();
      break;
    }
  }

  // rawSnippet: de zin(nen) rond de match als onderbouwing.
  let rawSnippet = replyBody.trim().slice(0, 400);
  const anchor = name ?? emails[0];
  if (anchor) {
    const idx = replyBody.indexOf(anchor.split(' ')[0]);
    if (idx >= 0) {
      rawSnippet = replyBody.slice(Math.max(0, idx - 120), idx + 200).trim();
    }
  }

  return {
    suggestedName: name,
    suggestedEmail: emails[0] ?? null,
    suggestedTitle: title,
    suggestedCompany: null,
    rawSnippet,
  };
}
