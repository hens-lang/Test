// Reply-classificatie (§8): keyword-heuristiek als fallback; AI (indien beschikbaar)
// zit in src/ai/classify.ts. Classificatie is altijd een voorstel — een teamlid bevestigt.
import type { ReplyClassification } from '@prisma/client';

interface Rule {
  classification: ReplyClassification;
  patterns: RegExp[];
}

// Volgorde is betekenisvol: eerste match wint.
const RULES: Rule[] = [
  {
    classification: 'BOUNCE',
    patterns: [
      /mailer-daemon/i, /delivery status notification/i, /undeliverable/i, /mail delivery failed/i,
      /address not found/i, /user unknown/i, /mailbox unavailable/i, /550[- ]5\.\d/,
    ],
  },
  {
    classification: 'UNSUBSCRIBE',
    patterns: [
      /afmelden/i, /uitschrijven/i, /unsubscribe/i, /verwijder (mij|ons|me)/i, /geen (mails?|e-?mails?) meer/i,
      /niet meer (mailen|benaderen)/i, /remove me/i, /stop met mailen/i,
    ],
  },
  {
    classification: 'OOO',
    patterns: [
      /out of office/i, /afwezig/i, /automatisch antwoord/i, /automatic reply/i, /auto-?reply/i,
      /ben (op vakantie|afwezig|niet aanwezig)/i, /tot \d{1,2}[-/ ]/i, /i am currently (out|away)/i,
      /met beperkte toegang tot (mijn )?e-?mail/i,
    ],
  },
  {
    classification: 'REFERRAL',
    patterns: [
      /moet je bij .{0,40}zijn/i, /kun je (beter )?bij/i, /collega/i, /verantwoordelijk voor/i,
      /doorgestuurd naar/i, /neem contact op met/i, /daarvoor is .{0,40}(de juiste|verantwoordelijk)/i,
      /you should (contact|reach out to)/i, /forwarded (this|your (mail|email)) to/i,
    ],
  },
  // NOT_NOW en NEGATIVE vóór POSITIVE: "geen interesse" mag nooit op /interesse/ matchen.
  {
    classification: 'NOT_NOW',
    patterns: [
      /niet op dit moment/i, /nu geen/i, /op dit moment (geen|niet)/i, /later dit jaar/i,
      /over (een paar|enkele|\d+) (weken|maanden)/i, /volgend (jaar|kwartaal)/i, /kom (er later|hier later) op terug/i,
      /not (right now|at this time|at the moment)/i, /maybe later/i, /in q[1-4]/i,
    ],
  },
  {
    classification: 'NEGATIVE',
    patterns: [
      /geen interesse/i, /niet ge[iï]nteresseerd/i, /geen behoefte/i, /gaan (er )?niet op in/i,
      /not interested/i, /no thank(s| you)/i, /we passen/i, /zijn al voorzien/i, /hebben al een/i,
    ],
  },
  {
    classification: 'POSITIVE',
    patterns: [
      /interessant/i, /interesse/i, /graag (een|meer)/i, /plan (maar|gerust)/i, /bel (me|mij|ons)/i,
      /afspraak/i, /kennismaking/i, /laten we/i, /stuur (maar|meer informatie)/i, /wanneer (kan|zou|past)/i,
      /sounds (good|interesting)/i, /let'?s (talk|schedule|meet)/i, /happy to (chat|talk|meet)/i,
    ],
  },
];

export function classifyReplyHeuristic(subject: string, body: string): ReplyClassification {
  const text = `${subject}\n${body}`;
  for (const rule of RULES) {
    if (rule.patterns.some((p) => p.test(text))) return rule.classification;
  }
  return 'OTHER';
}

/** Stopt deze classificatie de enrollment? (Alles behalve OOO; OOO pauzeert 7 dagen.) */
export function stopsEnrollment(c: ReplyClassification): boolean {
  return c !== 'OOO';
}

export const OOO_PAUSE_DAYS = 7;

/** Harde vs. zachte bounce-detectie uit DSN-tekst. */
export function isHardBounce(text: string): boolean {
  if (/5\.\d\.\d/.test(text) || /\b55[0-9]\b/.test(text)) return true;
  return /user unknown|address not found|does not exist|no such user|mailbox unavailable/i.test(text);
}

/** Spamklacht-detectie (FBL/abuse-replies). */
export function isComplaint(subject: string, body: string): boolean {
  const text = `${subject}\n${body}`;
  return /abuse report|feedback-type:\s*abuse|spam[- ]?(klacht|complaint)|this is spam|als spam gemarkeerd/i.test(text);
}
