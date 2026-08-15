// Personalisatie-engine (§6): genereert per enrollment een personalizedOpener.
// Met API-key via Anthropic; anders regelgebaseerd. Draait als backend-job.
import { prisma } from '@/lib/db';
import { aiComplete } from '@/ai/client';
import { hasAI } from '@/lib/env';
import { logger } from '@/lib/logger';
import {
  OPENER_SYSTEM_PROMPT,
  buildOpenerPrompt,
  FALLBACK_OPENERS,
  FALLBACK_OPENERS_NO_CITY,
  FALLBACK_OPENERS_MINIMAL,
} from './prompts';
import { renderTemplate } from '@/core/template';

/** Regelgebaseerde opener; varianten geselecteerd op een stabiele hash zodat niet elke mail identiek begint. */
export function fallbackOpener(input: {
  companyName: string;
  industry?: string | null;
  city?: string | null;
  seed: string;
}): string {
  const vars = { bedrijf: input.companyName, industry: input.industry ?? '', stad: input.city ?? '' };
  const pick = <T>(arr: T[]): T => {
    let h = 0;
    for (const ch of input.seed) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
    return arr[h % arr.length];
  };
  if (input.industry && input.city) {
    const r = renderTemplate(pick(FALLBACK_OPENERS), vars);
    if (r.ok) return r.text;
  }
  if (input.industry) {
    const r = renderTemplate(pick(FALLBACK_OPENERS_NO_CITY), vars);
    if (r.ok) return r.text;
  }
  const r = renderTemplate(pick(FALLBACK_OPENERS_MINIMAL), vars);
  return r.text;
}

/** Genereert (of hergenereert) de opener voor één enrollment. */
export async function generateOpener(enrollmentId: string): Promise<void> {
  const enrollment = await prisma.enrollment.findUnique({
    where: { id: enrollmentId },
    include: {
      contact: { include: { company: true } },
      campaign: true,
    },
  });
  if (!enrollment) return;
  if (enrollment.status !== 'PENDING_PERSONALIZATION') return;

  const { contact } = enrollment;
  const company = contact.company;
  let opener: string | null = null;

  if (hasAI()) {
    const res = await aiComplete(
      OPENER_SYSTEM_PROMPT,
      buildOpenerPrompt({
        companyName: company.name,
        industry: company.industry,
        city: company.city,
        websiteSummary: company.websiteSummary,
        contactTitle: contact.title,
      }),
      300,
    );
    if (res && res.text.length > 0 && res.text.length < 500) {
      opener = res.text;
      // Tokens/kosten per tenant loggen (§6).
      await prisma.auditLog.create({
        data: {
          action: 'ai_opener_generated',
          entity: 'Enrollment',
          entityId: enrollmentId,
          meta: { tenantId: contact.tenantId, inputTokens: res.usage.inputTokens, outputTokens: res.usage.outputTokens },
        },
      });
    }
  }
  if (!opener) {
    opener = fallbackOpener({
      companyName: company.name,
      industry: company.industry,
      city: company.city,
      seed: contact.id,
    });
  }

  const nextStatus = enrollment.campaign.requiresApproval ? 'PENDING_APPROVAL' : 'ACTIVE';
  await prisma.enrollment.update({
    where: { id: enrollmentId },
    data: { personalizedOpener: opener, status: nextStatus },
  });
  logger.info({ enrollmentId, nextStatus }, 'opener_generated');
}

/** Haalt de homepage op en vat samen tot ±100 woorden. Fouten zijn niet fataal. */
export async function summarizeWebsite(companyId: string): Promise<void> {
  const company = await prisma.company.findUnique({ where: { id: companyId } });
  if (!company || company.websiteSummary) return;

  try {
    const url = `https://${company.domain}`;
    // robots.txt respecteren voor de homepage-fetch.
    const robotsRes = await fetch(`https://${company.domain}/robots.txt`, {
      headers: { 'User-Agent': 'LINK-Outreach/1.0 (+https://linkgrp.nl)' },
      signal: AbortSignal.timeout(5000),
    }).catch(() => null);
    if (robotsRes?.ok) {
      const robots = await robotsRes.text();
      if (disallowsRoot(robots)) {
        logger.info({ companyId }, 'website_fetch_disallowed_by_robots');
        return;
      }
    }

    const res = await fetch(url, {
      headers: { 'User-Agent': 'LINK-Outreach/1.0 (+https://linkgrp.nl)' },
      signal: AbortSignal.timeout(10000),
      redirect: 'follow',
    });
    if (!res.ok) return;
    const html = await res.text();
    const text = extractText(html).slice(0, 6000);
    if (text.length < 100) return;

    let summary: string | null = null;
    if (hasAI()) {
      const ai = await aiComplete(
        'Vat de volgende websitetekst samen in maximaal 100 Nederlandse woorden. Focus op: wat doet het bedrijf, voor wie, en wat maakt het onderscheidend. Antwoord met alleen de samenvatting.',
        text,
        300,
      );
      summary = ai?.text ?? null;
    }
    if (!summary) {
      // Fallback: eerste zinvolle tekstfragment als ruwe samenvatting.
      summary = text.split(/(?<=[.!?])\s+/).slice(0, 5).join(' ').slice(0, 600);
    }
    await prisma.company.update({ where: { id: companyId }, data: { websiteSummary: summary } });
  } catch (err) {
    logger.info({ companyId, err: String(err) }, 'website_summary_failed');
  }
}

export function disallowsRoot(robotsTxt: string): boolean {
  const lines = robotsTxt.split('\n').map((l) => l.trim().toLowerCase());
  let inStar = false;
  for (const line of lines) {
    if (line.startsWith('user-agent:')) inStar = line.includes('*');
    else if (inStar && (line === 'disallow: /' || line === 'disallow:/')) return true;
  }
  return false;
}

export function extractText(html: string): string {
  return html
    .replace(/<script[\s\S]*?<\/script>/gi, ' ')
    .replace(/<style[\s\S]*?<\/style>/gi, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&[a-z]+;/gi, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}
