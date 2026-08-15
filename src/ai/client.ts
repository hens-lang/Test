// Optionele Anthropic-client. Zonder ANTHROPIC_API_KEY valt elk onderdeel terug
// op een regelgebaseerd alternatief — de aanroepende code checkt hasAI() eerst.
// Rate-limit: max 3 parallelle calls, retry met exponentiële backoff (§6).
import Anthropic from '@anthropic-ai/sdk';
import { getAnthropicKey } from '@/lib/env';
import { logger } from '@/lib/logger';

const MODEL = 'claude-sonnet-5';
const MAX_PARALLEL = 3;
const MAX_RETRIES = 3;

let client: Anthropic | null = null;
let active = 0;
const waiters: (() => void)[] = [];

function getClient(): Anthropic | null {
  const key = getAnthropicKey();
  if (!key) return null;
  if (!client) client = new Anthropic({ apiKey: key });
  return client;
}

async function acquire(): Promise<void> {
  if (active < MAX_PARALLEL) {
    active += 1;
    return;
  }
  await new Promise<void>((resolve) => waiters.push(resolve));
  active += 1;
}

function release(): void {
  active -= 1;
  const next = waiters.shift();
  if (next) next();
}

export interface AiUsage {
  inputTokens: number;
  outputTokens: number;
}

/**
 * Eén tekst-completion met concurrency-limiet en retry/backoff.
 * Geeft null terug als er geen API-key is of alle retries falen (caller valt terug op regels).
 */
export async function aiComplete(
  system: string,
  user: string,
  maxTokens = 500,
): Promise<{ text: string; usage: AiUsage } | null> {
  const c = getClient();
  if (!c) return null;
  await acquire();
  try {
    for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
      try {
        const res = await c.messages.create({
          model: MODEL,
          max_tokens: maxTokens,
          system,
          messages: [{ role: 'user', content: user }],
        });
        const text = res.content
          .filter((b): b is Anthropic.TextBlock => b.type === 'text')
          .map((b) => b.text)
          .join('')
          .trim();
        return {
          text,
          usage: { inputTokens: res.usage.input_tokens, outputTokens: res.usage.output_tokens },
        };
      } catch (err) {
        logger.warn({ attempt, err: String(err) }, 'ai_call_failed');
        if (attempt === MAX_RETRIES - 1) return null;
        await new Promise((r) => setTimeout(r, 1000 * 2 ** attempt));
      }
    }
    return null;
  } finally {
    release();
  }
}
