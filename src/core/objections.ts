// Bezwarenclustering: waarom zegt de markt "nee" of "nu niet"?
// Regelgebaseerd (NL+EN); de AI-variant in src/ai kan clusters verfijnen.
// Geaggregeerd per maand wordt dit een marktsignaal: verschuivende bezwaren
// vertellen wat er in de markt van de klant gebeurt.

export type ObjectionCluster =
  | 'AL_VOORZIEN'
  | 'GEEN_BUDGET'
  | 'SLECHTE_TIMING'
  | 'GEEN_BEHOEFTE'
  | 'DOET_HET_ZELF'
  | 'ANDERS';

export const OBJECTION_LABELS: Record<ObjectionCluster, string> = {
  AL_VOORZIEN: 'Al voorzien / vaste leverancier',
  GEEN_BUDGET: 'Geen budget / te duur',
  SLECHTE_TIMING: 'Timing — nu niet, later wel',
  GEEN_BEHOEFTE: 'Geen behoefte',
  DOET_HET_ZELF: 'Doen het zelf / intern opgelost',
  ANDERS: 'Overig',
};

/** Advies per cluster — dit maakt de analyse actiegericht i.p.v. beschrijvend. */
export const OBJECTION_ADVICE: Record<ObjectionCluster, string> = {
  AL_VOORZIEN: 'Benoem in de eerste mail expliciet waarin het aanbod verschilt van een zittende leverancier, en vraag naar het contractmoment.',
  GEEN_BUDGET: 'Verschuif de boodschap van kosten naar opbrengst/risico, of richt op segmenten met investeringsruimte.',
  SLECHTE_TIMING: 'Zet deze prospects in de heractiveringswachtrij — deze groep komt terug en is dan warm.',
  GEEN_BEHOEFTE: 'Controleer de doelgroepselectie: dit segment herkent het probleem (nog) niet — overweeg een andere insteek of ander segment.',
  DOET_HET_ZELF: 'Positioneer als aanvulling op het interne team in plaats van vervanging.',
  ANDERS: 'Lees de citaten — hier kunnen nieuwe patronen in zitten die een eigen cluster verdienen.',
};

const RULES: { cluster: ObjectionCluster; patterns: RegExp[] }[] = [
  {
    cluster: 'AL_VOORZIEN',
    patterns: [
      /al (een |eigen )?(leverancier|partij|partner|bureau|contract)/i, /al voorzien/i,
      /hebben (hier)? ?al (een|iemand)/i, /tevreden (met|over) (onze|de|ons) huidige/i,
      /vast(e)? (leverancier|partner|partij)/i, /already (have|working with|covered)/i,
    ],
  },
  {
    cluster: 'GEEN_BUDGET',
    patterns: [
      /geen budget/i, /budget (is )?(bevroren|op|beperkt)/i, /bezuinig/i, /te duur/i,
      /geen (financi[eë]le )?ruimte/i, /kosten(plaatje)? (te hoog|liggen)/i, /no budget/i, /too expensive/i,
    ],
  },
  {
    cluster: 'SLECHTE_TIMING',
    patterns: [
      /niet op dit moment/i, /nu (even )?geen/i, /later dit jaar/i, /volgend (jaar|kwartaal)/i,
      /over (een paar|enkele|\d+) (weken|maanden)/i, /kom .{0,20}terug/i, /reorganisatie/i,
      /(erg|te) druk/i, /verkeerde moment/i, /not (right now|at this time)/i, /bad timing/i,
    ],
  },
  {
    cluster: 'DOET_HET_ZELF',
    patterns: [
      /doen (dit|alles|het) (zelf|intern)/i, /eigen (team|mensen|afdeling)/i, /in eigen beheer/i,
      /intern (opgelost|geregeld|belegd)/i, /in-?house/i,
    ],
  },
  {
    cluster: 'GEEN_BEHOEFTE',
    patterns: [
      /geen behoefte/i, /niet nodig/i, /geen interesse/i, /niet relevant/i, /speelt (bij ons )?niet/i,
      /no need/i, /not interested/i,
    ],
  },
];

export function clusterObjection(text: string): ObjectionCluster {
  for (const rule of RULES) {
    if (rule.patterns.some((p) => p.test(text))) return rule.cluster;
  }
  return 'ANDERS';
}

export interface ObjectionStats {
  cluster: ObjectionCluster;
  label: string;
  count: number;
  share: number; // 0-1 van alle bezwaren
  quotes: string[]; // korte letterlijke citaten als onderbouwing
  advice: string;
}

export function aggregateObjections(texts: string[], maxQuotes = 3): ObjectionStats[] {
  const buckets = new Map<ObjectionCluster, string[]>();
  for (const t of texts) {
    const c = clusterObjection(t);
    const list = buckets.get(c) ?? [];
    list.push(t.replace(/\s+/g, ' ').trim().slice(0, 160));
    buckets.set(c, list);
  }
  const total = texts.length || 1;
  return [...buckets.entries()]
    .map(([cluster, quotes]) => ({
      cluster,
      label: OBJECTION_LABELS[cluster],
      count: quotes.length,
      share: quotes.length / total,
      quotes: quotes.slice(0, maxQuotes),
      advice: OBJECTION_ADVICE[cluster],
    }))
    .sort((a, b) => b.count - a.count);
}

/** Functietitels normaliseren naar groepen zodat segmentanalyse betekenis krijgt. */
export function titleGroup(title: string | null | undefined): string {
  if (!title) return 'Onbekend';
  const t = title.toLowerCase();
  if (/(directeur|director|ceo|cfo|coo|dga|eigenaar|owner|founder|oprichter)/.test(t)) return 'Directie';
  if (/(inkoop|procurement|purchas)/.test(t)) return 'Inkoop';
  if (/(operat|productie|logistiek|planning|supply)/.test(t)) return 'Operationeel';
  if (/(commercieel|sales|verkoop|business develop|account)/.test(t)) return 'Commercieel';
  if (/(marketing|communicatie)/.test(t)) return 'Marketing';
  if (/(hr|human resource|personeel|recruit)/.test(t)) return 'HR';
  if (/(it|ict|tech|software|digital)/.test(t)) return 'IT';
  if (/(office|management ?assistent|secretar|recepti)/.test(t)) return 'Officemanagement';
  if (/(manager|hoofd|lead|teamleider|chef)/.test(t)) return 'Management';
  return 'Overig';
}
