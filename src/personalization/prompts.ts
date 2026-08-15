// Prompts en few-shot-voorbeelden voor de personalisatie-engine (§6).
// Bewust een apart, makkelijk aanpasbaar bestand.

export const OPENER_SYSTEM_PROMPT = `Je schrijft openingszinnen voor Nederlandse B2B-e-mails namens LINK., een leadgeneratiebureau.

Regels:
- Schrijf 1 à 2 korte, natuurlijke Nederlandse zinnen.
- Verwijs concreet naar wat het bedrijf doet (gebruik de meegegeven samenvatting).
- Geen clichés als "Ik hoop dat het goed gaat", "Ik kom graag in contact" of "Mijn naam is".
- Geen aanhef (geen "Beste ..." — die staat al in de mail).
- Geen aanbiedingen of pitch — alleen een relevante, persoonlijke observatie.
- Toon: professioneel maar menselijk, niet slijmerig.

Antwoord met ALLEEN de openingszin(nen), zonder aanhalingstekens of uitleg.`;

export const OPENER_FEW_SHOTS: { input: string; output: string }[] = [
  {
    input:
      'Bedrijf: Bakkerij De Korenaar (bakkerij, Utrecht). Samenvatting: Ambachtelijke bakkerij met drie vestigingen in Utrecht, bekend om desembrood en levering aan horeca.',
    output:
      'Drie vestigingen én horecaleveringen — De Korenaar is duidelijk meer dan een buurtbakker. Juist bij die groei wordt nieuwe B2B-aanwas belangrijk.',
  },
  {
    input:
      'Bedrijf: Van Dijk Logistics (transport, Rotterdam). Samenvatting: Familiebedrijf in koeltransport voor de voedingsindustrie, actief in de Benelux, 85 vrachtwagens.',
    output:
      'Koeltransport voor de voedingsindustrie met 85 wagens in de Benelux: dan weet u als geen ander dat continuïteit in opdrachten alles is.',
  },
  {
    input:
      'Bedrijf: CloudWorks (IT-diensten, Amsterdam). Samenvatting: MSP die MKB-bedrijven ontzorgt met werkplekbeheer, Microsoft 365 en security.',
    output:
      'Werkplekbeheer en security voor het MKB is een markt waar vertrouwen alles bepaalt — precies daarom werkt een warme introductie daar zoveel beter dan een koude.',
  },
];

export function buildOpenerPrompt(input: {
  companyName: string;
  industry?: string | null;
  city?: string | null;
  websiteSummary?: string | null;
  contactTitle?: string | null;
}): string {
  const shots = OPENER_FEW_SHOTS.map((s) => `Voorbeeld:\n${s.input}\nOpeningszin: ${s.output}`).join('\n\n');
  const summary = input.websiteSummary || 'Geen samenvatting beschikbaar.';
  return `${shots}\n\nNu jij:\nBedrijf: ${input.companyName}${input.industry ? ` (${input.industry}` : ''}${
    input.city ? `${input.industry ? ', ' : ' ('}${input.city})` : input.industry ? ')' : ''
  }. Functie contactpersoon: ${input.contactTitle || 'onbekend'}. Samenvatting: ${summary}\nOpeningszin:`;
}

// Regelgebaseerde fallback-openers (zonder API-key). Meerdere varianten zodat
// niet elke mail identiek begint. Variabelen worden later gerenderd/gevalideerd.
export const FALLBACK_OPENERS: string[] = [
  'Ik zag dat {{bedrijf}} actief is in {{industry}} in {{stad}}.',
  'Ik kwam {{bedrijf}} tegen tijdens onderzoek naar {{industry}}-bedrijven in de regio {{stad}}.',
  '{{bedrijf}} viel mij op tussen de {{industry}}-bedrijven in {{stad}}.',
  'Bij het bekijken van {{industry}}-bedrijven in {{stad}} kwam ik uit bij {{bedrijf}}.',
];

export const FALLBACK_OPENERS_NO_CITY: string[] = [
  'Ik zag dat {{bedrijf}} actief is in {{industry}}.',
  'Ik kwam {{bedrijf}} tegen tijdens onderzoek naar bedrijven in {{industry}}.',
  '{{bedrijf}} viel mij op binnen {{industry}}.',
];

export const FALLBACK_OPENERS_MINIMAL: string[] = [
  'Ik kwam {{bedrijf}} onlangs tegen en was benieuwd naar jullie plannen.',
  '{{bedrijf}} kwam bij ons naar voren als interessant bedrijf om mee te schakelen.',
];
