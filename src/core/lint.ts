// Content-lint (§7e): spam-check vóór activatie. Blockers moeten opgelost; warnings zijn advies.

export interface LintIssue {
  level: 'blocker' | 'warning';
  code: string;
  message: string;
}

// NL + EN spam-triggerwoorden (uitbreidbaar in config).
export const SPAM_WORDS = [
  'gratis!!', 'gegarandeerd', 'geen verplichtingen', '100% gratis', 'verdien geld',
  'snel geld', 'eenmalige kans', 'nu kopen', 'exclusieve deal', 'klik hier',
  'free!!', 'guaranteed', 'no obligation', 'act now', 'make money', 'earn cash',
  'risk free', 'winner', 'congratulations', 'click here', 'limited time', 'buy now',
];

const LINK_RE = /https?:\/\/[^\s>"')]+/gi;

export function lintSubject(subject: string): LintIssue[] {
  const issues: LintIssue[] = [];
  if (subject.includes('!')) {
    issues.push({ level: 'blocker', code: 'subject_exclamation', message: 'Uitroepteken in onderwerpsregel' });
  }
  if (subject.length > 65) {
    issues.push({ level: 'warning', code: 'subject_long', message: `Onderwerpsregel is lang (${subject.length} tekens, advies ≤ 65)` });
  }
  const letters = subject.replace(/[^a-zA-Z]/g, '');
  if (letters.length >= 4 && letters === letters.toUpperCase()) {
    issues.push({ level: 'blocker', code: 'subject_caps', message: 'Onderwerpsregel in ALL CAPS' });
  }
  issues.push(...spamWordIssues(subject, 'onderwerp'));
  return issues;
}

export function lintBody(body: string, opts: { hasUnsubscribeVar?: boolean } = {}): LintIssue[] {
  const issues: LintIssue[] = [];
  const links = body.match(LINK_RE) ?? [];
  if (links.length > 1) {
    issues.push({ level: 'blocker', code: 'too_many_links', message: `Meer dan 1 link in de mail (${links.length} gevonden)` });
  }
  const letters = body.replace(/\{\{[^}]+\}\}/g, '').replace(/[^a-zA-Z\s]/g, '');
  const words = letters.split(/\s+/).filter((w) => w.length >= 4);
  const capsWords = words.filter((w) => w === w.toUpperCase());
  if (words.length > 0 && capsWords.length / words.length > 0.3) {
    issues.push({ level: 'blocker', code: 'body_caps', message: 'Te veel woorden in ALL CAPS' });
  }
  issues.push(...spamWordIssues(body, 'tekst'));
  const textOnly = body.replace(/<[^>]+>/g, '').trim();
  if (textOnly.length < 20 && body.includes('<img')) {
    issues.push({ level: 'blocker', code: 'image_only', message: 'Mail bevat vrijwel alleen beeld, geen tekst' });
  }
  if (!opts.hasUnsubscribeVar) {
    // De afmeldlink wordt door de verzendengine altijd in de footer geïnjecteerd;
    // dit is een informatieve check voor wie de link zelf in de body wil zetten.
    issues.push({ level: 'warning', code: 'no_unsubscribe_in_body', message: 'Geen afmeldlink in de body — wordt automatisch in de footer toegevoegd' });
  }
  return issues;
}

function spamWordIssues(text: string, where: string): LintIssue[] {
  const lower = text.toLowerCase();
  const hits = SPAM_WORDS.filter((w) => lower.includes(w));
  return hits.map((w) => ({
    level: 'blocker' as const,
    code: 'spam_word',
    message: `Spam-triggerwoord "${w}" in ${where}`,
  }));
}

export interface StepTemplate {
  subjectA: string;
  bodyA: string;
  subjectB?: string | null;
  bodyB?: string | null;
}

export function lintSequence(steps: StepTemplate[]): LintIssue[] {
  const issues: LintIssue[] = [];
  if (steps.length === 0) {
    issues.push({ level: 'blocker', code: 'no_steps', message: 'Campagne heeft geen stappen' });
  }
  steps.forEach((s, i) => {
    const prefix = `Stap ${i + 1}`;
    for (const issue of [...lintSubject(s.subjectA), ...lintBody(s.bodyA)]) {
      issues.push({ ...issue, message: `${prefix} (A): ${issue.message}` });
    }
    if (s.subjectB && s.bodyB) {
      for (const issue of [...lintSubject(s.subjectB), ...lintBody(s.bodyB)]) {
        issues.push({ ...issue, message: `${prefix} (B): ${issue.message}` });
      }
    }
  });
  return issues;
}

export function hasBlockers(issues: LintIssue[]): boolean {
  return issues.some((i) => i.level === 'blocker');
}
