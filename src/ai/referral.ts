// AI-referral-extractie met regelgebaseerde fallback (§9).
import { aiComplete } from './client';
import { extractReferralHeuristic, type ReferralExtraction } from '@/core/referral-extract';
import { hasAI } from '@/lib/env';

export async function extractReferral(replyBody: string, replierEmail?: string): Promise<ReferralExtraction> {
  if (hasAI()) {
    const res = await aiComplete(
      `Uit een e-mailreply waarin iemand doorverwijst naar een andere persoon, extraheer je:
naam, e-mailadres (ALLEEN als het letterlijk in de tekst staat — nooit raden of afleiden),
functie en bedrijf van de doorverwezen persoon. Antwoord in strikt JSON:
{"name": string|null, "email": string|null, "title": string|null, "company": string|null, "snippet": string}
waarbij snippet het letterlijke tekstfragment is waarin de verwijzing staat.`,
      replyBody,
      300,
    );
    if (res) {
      try {
        const raw = res.text.replace(/^```json?\s*/i, '').replace(/```\s*$/, '');
        const parsed = JSON.parse(raw);
        const email = typeof parsed.email === 'string' ? parsed.email.toLowerCase() : null;
        // Hard vangnet: het adres moet letterlijk in de reply staan (nooit gegenereerd).
        const emailInText = email && replyBody.toLowerCase().includes(email) ? email : null;
        return {
          suggestedName: typeof parsed.name === 'string' ? parsed.name : null,
          suggestedEmail: emailInText,
          suggestedTitle: typeof parsed.title === 'string' ? parsed.title : null,
          suggestedCompany: typeof parsed.company === 'string' ? parsed.company : null,
          rawSnippet: typeof parsed.snippet === 'string' ? parsed.snippet.slice(0, 400) : replyBody.slice(0, 400),
        };
      } catch {
        // val door naar heuristiek
      }
    }
  }
  return extractReferralHeuristic(replyBody, replierEmail);
}
