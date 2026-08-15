// Prompts voor de AI-reply-assistent (§10). Apart bestand, makkelijk aanpasbaar.
import type { ReplyClassification } from '@prisma/client';

export const REPLY_SYSTEM_PROMPT = `Je schrijft conceptantwoorden op e-mailreplies namens een B2B-bedrijf.
Je krijgt: het tone-of-voice-profiel van de afzender, de campagne-propositie, de volledige conversatie en de classificatie van de laatste reply.

Regels:
- Schrijf in het Nederlands, in de stijl van het tone-of-voice-profiel (let op je/u).
- Kort en concreet; geen herhaling van de hele propositie.
- POSITIVE: bedank, stuur aan op een afspraak en stel twee concrete momenten voor (bijv. "dinsdag om 10:00 of donderdag om 14:00").
- NOT_NOW: bevestig vriendelijk, vraag toestemming om over enkele maanden terug te komen.
- REFERRAL: bedank hartelijk en kondig aan dat de doorverwezen persoon benaderd wordt.
- NEGATIVE: sluit kort en netjes af, houd de deur op een kier.
- Geen onderwerpsregel in je antwoord — alleen de bodytekst.
- Onderteken met alleen de voornaam van de afzender als die bekend is, anders zonder ondertekening.

Antwoord met ALLEEN de conceptmail.`;

export function buildReplyPrompt(input: {
  toneOfVoice: string | null;
  proposition: string | null;
  conversation: { direction: 'OUT' | 'IN'; subject: string; body: string }[];
  classification: ReplyClassification;
}): string {
  const convo = input.conversation
    .map((m) => `${m.direction === 'OUT' ? 'WIJ' : 'PROSPECT'}: ${m.subject}\n${m.body}`)
    .join('\n---\n');
  return `Tone of voice:\n${input.toneOfVoice || 'Professioneel, vriendelijk, u-vorm.'}\n\nPropositie:\n${
    input.proposition || 'Niet opgegeven.'
  }\n\nClassificatie van de laatste reply: ${input.classification}\n\nConversatie:\n${convo}\n\nSchrijf het conceptantwoord:`;
}

// Statische fallback-templates per classificatie (zonder API-key), per tenant aanpasbaar
// via tenant-instellingen; dit zijn de defaults.
export const FALLBACK_REPLY_TEMPLATES: Partial<Record<ReplyClassification, string>> = {
  POSITIVE:
    'Dank voor uw reactie, goed om te horen dat het interessant klinkt.\n\nZullen we kort kennismaken? Ik kan bijvoorbeeld dinsdag om 10:00 of donderdag om 14:00. Als een ander moment beter past, hoor ik het graag.\n\nMet vriendelijke groet',
  NOT_NOW:
    'Dank voor uw eerlijke reactie, helder dat het er nu niet van komt.\n\nVindt u het goed als ik over een paar maanden nog eens contact opneem om te kijken of het dan beter past?\n\nMet vriendelijke groet',
  REFERRAL:
    'Hartelijk dank voor het doorverwijzen — dat waardeer ik zeer.\n\nIk neem contact op met uw collega en verwijs daarbij kort naar dit gesprek.\n\nMet vriendelijke groet',
  NEGATIVE:
    'Dank voor uw duidelijke reactie. Dan laat ik het hierbij.\n\nMocht de situatie in de toekomst veranderen, dan weet u ons te vinden.\n\nMet vriendelijke groet',
  OTHER:
    'Dank voor uw bericht.\n\n[Concept: beoordeel de reply en schrijf hier een passend antwoord.]\n\nMet vriendelijke groet',
};
