// AI-reply-assistent (§10): genereert een ReplyDraft per inkomende reply.
// Nooit automatisch versturen — een teamlid beoordeelt in de reply-inbox.
import { prisma } from '@/lib/db';
import { aiComplete } from '@/ai/client';
import { hasAI } from '@/lib/env';
import { REPLY_SYSTEM_PROMPT, buildReplyPrompt, FALLBACK_REPLY_TEMPLATES } from './prompts';
import { logger } from '@/lib/logger';

export async function generateReplyDraft(messageId: string): Promise<void> {
  const message = await prisma.message.findUnique({
    where: { id: messageId },
    include: { enrollment: { include: { campaign: true } }, tenant: true },
  });
  if (!message || message.direction !== 'IN') return;
  // Geen concepten voor bounces en unsubscribes (§10).
  if (message.classifiedAs === 'BOUNCE' || message.classifiedAs === 'UNSUBSCRIBE' || message.classifiedAs === 'OOO') return;
  const existing = await prisma.replyDraft.findFirst({ where: { messageId } });
  if (existing) return;

  const classification = message.classifiedAs ?? 'OTHER';
  let draftBody: string | null = null;
  let generatedBy: 'AI' | 'RULE' = 'RULE';

  if (hasAI()) {
    const conversation = message.enrollmentId
      ? await prisma.message.findMany({
          where: { enrollmentId: message.enrollmentId },
          orderBy: { createdAt: 'asc' },
          select: { direction: true, subject: true, body: true },
        })
      : [{ direction: message.direction, subject: message.subject, body: message.body }];
    const res = await aiComplete(
      REPLY_SYSTEM_PROMPT,
      buildReplyPrompt({
        toneOfVoice: message.tenant.toneOfVoice,
        proposition: message.enrollment?.campaign.proposition ?? null,
        conversation: conversation.map((m) => ({ direction: m.direction, subject: m.subject, body: m.body })),
        classification,
      }),
      600,
    );
    if (res && res.text.length > 20) {
      draftBody = res.text;
      generatedBy = 'AI';
      await prisma.auditLog.create({
        data: {
          action: 'ai_reply_draft_generated',
          entity: 'Message',
          entityId: messageId,
          meta: { tenantId: message.tenantId, inputTokens: res.usage.inputTokens, outputTokens: res.usage.outputTokens },
        },
      });
    }
  }
  if (!draftBody) {
    draftBody = FALLBACK_REPLY_TEMPLATES[classification] ?? FALLBACK_REPLY_TEMPLATES.OTHER!;
  }

  await prisma.replyDraft.create({
    data: {
      messageId,
      tenantId: message.tenantId,
      draftSubject: message.subject.startsWith('Re:') ? message.subject : `Re: ${message.subject}`,
      draftBody,
      generatedBy,
    },
  });
  logger.info({ messageId, generatedBy }, 'reply_draft_created');
}

/**
 * Kwaliteitsmetriek (§10): hoe zwaar worden AI-concepten bewerkt voor verzending?
 * Simpele afstandsmaat op woordniveau, als percentage.
 */
export function editDistancePercent(draft: string, final: string): number {
  const a = draft.trim().split(/\s+/);
  const b = final.trim().split(/\s+/);
  if (a.length === 0 && b.length === 0) return 0;
  const setA = new Set(a);
  const setB = new Set(b);
  let common = 0;
  for (const w of setA) if (setB.has(w)) common += 1;
  const union = new Set([...a, ...b]).size;
  return Math.round((1 - common / union) * 100);
}
