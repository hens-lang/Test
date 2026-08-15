import pino from 'pino';

// Gestructureerde logs. Persoonsgegevens (e-mailadressen, namen) horen hier NIET in —
// log id's, geen inhoud. redact vangt veelvoorkomende sleutel-namen af als vangnet.
export const logger = pino({
  level: process.env.LOG_LEVEL || 'info',
  redact: {
    paths: ['email', '*.email', 'firstName', 'lastName', '*.firstName', '*.lastName', 'body', '*.body', 'password', '*.password'],
    censor: '[redacted]',
  },
});

// Foutmonitoring-hook: koppel hier bijv. Sentry aan. Bewust een enkel punt.
export function reportError(err: unknown, context?: Record<string, unknown>) {
  logger.error({ err, ...context }, 'unhandled_error');
}
