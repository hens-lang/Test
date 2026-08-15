import { describe, it, expect } from 'vitest';
import { lintSubject, lintBody, lintSequence, hasBlockers } from '@/core/lint';

describe('content-lint (§7e)', () => {
  it('blokkeert uitroeptekens in het onderwerp', () => {
    expect(lintSubject('Kans voor u!').some((i) => i.level === 'blocker')).toBe(true);
  });
  it('blokkeert ALL CAPS onderwerp', () => {
    expect(lintSubject('GRATIS DEMO NU').some((i) => i.code === 'subject_caps')).toBe(true);
  });
  it('blokkeert spam-triggerwoorden (NL+EN)', () => {
    expect(lintSubject('Dit is gegarandeerd iets voor u').some((i) => i.code === 'spam_word')).toBe(true);
    expect(lintBody('This is guaranteed to work').some((i) => i.code === 'spam_word')).toBe(true);
  });
  it('blokkeert meer dan 1 link', () => {
    const issues = lintBody('Zie https://a.nl en https://b.nl');
    expect(issues.some((i) => i.code === 'too_many_links')).toBe(true);
  });
  it('een nette mail heeft geen blockers', () => {
    const issues = lintSequence([{
      subjectA: 'Vraag over groei bij {{bedrijf}}',
      bodyA: 'Beste {{voornaam}},\n\n{{opener}}\n\nZou een kennismaking interessant zijn?\n\nMet vriendelijke groet',
    }]);
    expect(hasBlockers(issues)).toBe(false);
  });
  it('een lege sequence is een blocker', () => {
    expect(hasBlockers(lintSequence([]))).toBe(true);
  });
});
