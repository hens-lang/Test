// Centrale, gevalideerde toegang tot omgevingsvariabelen.
// Nooit rechtstreeks process.env gebruiken buiten dit bestand (behalve NODE_ENV).

export type SendMode = 'demo' | 'live';

export function getSendMode(): SendMode {
  return process.env.SEND_MODE === 'live' ? 'live' : 'demo';
}

export function getAppUrl(): string {
  return process.env.APP_URL || 'http://localhost:3000';
}

export function getSessionSecret(): string {
  const s = process.env.SESSION_SECRET;
  if (!s || s.length < 16) {
    if (process.env.NODE_ENV === 'production') {
      throw new Error('SESSION_SECRET ontbreekt of is te kort');
    }
    return 'dev-only-session-secret-not-for-production';
  }
  return s;
}

export function getEncryptionKey(): Buffer {
  const hex = process.env.ENCRYPTION_KEY;
  if (!hex || hex.length !== 64) {
    if (process.env.NODE_ENV === 'production') {
      throw new Error('ENCRYPTION_KEY moet 32 bytes hex zijn (64 tekens)');
    }
    // Deterministische dev-sleutel zodat lokaal ontwikkelen zonder setup werkt.
    return Buffer.from('00'.repeat(32), 'hex');
  }
  return Buffer.from(hex, 'hex');
}

export function getAnthropicKey(): string | null {
  const k = process.env.ANTHROPIC_API_KEY;
  return k && k.trim().length > 0 ? k : null;
}

export function hasAI(): boolean {
  return getAnthropicKey() !== null;
}
