// AI-classificatie van replies (met heuristische fallback in core/classify.ts).
import type { ReplyClassification } from '@prisma/client';
import { aiComplete } from './client';
import { classifyReplyHeuristic } from '@/core/classify';
import { hasAI } from '@/lib/env';

const VALID: ReplyClassification[] = ['POSITIVE', 'REFERRAL', 'NOT_NOW', 'NEGATIVE', 'OOO', 'UNSUBSCRIBE', 'OTHER'];

export async function classifyReply(subject: string, body: string): Promise<ReplyClassification> {
  if (hasAI()) {
    const res = await aiComplete(
      `Classificeer een e-mailreply op een B2B cold-mail in precies één categorie:
POSITIVE (interesse, wil afspraak/meer info), REFERRAL (verwijst naar een collega/andere persoon),
NOT_NOW (nu niet, later misschien), NEGATIVE (geen interesse), OOO (afwezigheidsbericht),
UNSUBSCRIBE (wil geen mail meer), OTHER (al het overige).
Antwoord met alleen het categorielabel.`,
      `Onderwerp: ${subject}\n\n${body}`,
      10,
    );
    const label = res?.text.trim().toUpperCase();
    if (label && (VALID as string[]).includes(label)) return label as ReplyClassification;
  }
  return classifyReplyHeuristic(subject, body);
}
