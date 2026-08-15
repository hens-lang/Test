// Guardrails (§7d): automatische stop-regels, hard afgedwongen in de backend.
// Pure beslislogica; de jobs passen de uitkomst toe.

export const CAMPAIGN_BOUNCE_WINDOW = 100;
export const CAMPAIGN_BOUNCE_THRESHOLD = 0.03; // 3%
export const MAILBOX_BOUNCE_THRESHOLD = 0.05; // 5% op een dag
export const MAILBOX_SMTP_ERROR_LIMIT = 3; // op rij
export const DOMAIN_COMPLAINT_LIMIT = 2;

export interface GuardrailDecision {
  pause: boolean;
  reason?: string;
}

/** Campagne: bounce-rate > 3% over de laatste 100 verzonden mails → PAUSED. */
export function checkCampaignBounceRate(sentInWindow: number, bouncedInWindow: number): GuardrailDecision {
  if (sentInWindow < CAMPAIGN_BOUNCE_WINDOW) return { pause: false };
  const rate = bouncedInWindow / sentInWindow;
  if (rate > CAMPAIGN_BOUNCE_THRESHOLD) {
    return { pause: true, reason: `Bounce-rate ${(rate * 100).toFixed(1)}% > 3% over laatste ${sentInWindow} mails` };
  }
  return { pause: false };
}

/** Mailbox: >5% bounces op een dag of 3 SMTP-fouten op rij → PAUSED. */
export function checkMailboxHealth(state: {
  sentToday: number;
  bouncedToday: number;
  consecutiveSmtpErrors: number;
}): GuardrailDecision {
  if (state.consecutiveSmtpErrors >= MAILBOX_SMTP_ERROR_LIMIT) {
    return { pause: true, reason: `${state.consecutiveSmtpErrors} SMTP-fouten op rij` };
  }
  if (state.sentToday >= 20 && state.bouncedToday / state.sentToday > MAILBOX_BOUNCE_THRESHOLD) {
    return {
      pause: true,
      reason: `Bounce-rate vandaag ${((state.bouncedToday / state.sentToday) * 100).toFixed(1)}% > 5%`,
    };
  }
  return { pause: false };
}

/** Domein: ≥2 spamklachten → PAUSED. */
export function checkDomainComplaints(complaintCount: number): GuardrailDecision {
  if (complaintCount >= DOMAIN_COMPLAINT_LIMIT) {
    return { pause: true, reason: `${complaintCount} spamklachten op dit domein` };
  }
  return { pause: false };
}

/**
 * Harde verzendpoort: mag deze mail nu de deur uit?
 * Wordt in de verzendjob zelf gecontroleerd — niet alleen in de UI.
 */
export interface SendGateInput {
  domainStatus: string;
  domainSpfOk: boolean;
  domainDkimOk: boolean;
  mailboxStatus: string;
  mailboxSentToday: number;
  mailboxDailyCap: number;
  campaignStatus: string;
  enrollmentStatus: string;
  suppressed: boolean;
  emailStatus: string;
  hasUnsubscribeLink: boolean;
}

export function canSend(input: SendGateInput): { allowed: boolean; reason?: string } {
  if (input.suppressed) return { allowed: false, reason: 'Adres staat op de suppressielijst' };
  if (!input.domainSpfOk || !input.domainDkimOk) return { allowed: false, reason: 'Domein heeft geen geldige SPF+DKIM' };
  if (input.domainStatus !== 'ACTIVE' && input.domainStatus !== 'WARMING') {
    return { allowed: false, reason: `Domeinstatus is ${input.domainStatus}` };
  }
  if (input.mailboxStatus !== 'ACTIVE' && input.mailboxStatus !== 'WARMING') {
    return { allowed: false, reason: `Mailboxstatus is ${input.mailboxStatus}` };
  }
  if (input.mailboxSentToday >= input.mailboxDailyCap) {
    return { allowed: false, reason: 'Dagcap van de mailbox bereikt' };
  }
  if (input.campaignStatus !== 'ACTIVE') return { allowed: false, reason: `Campagnestatus is ${input.campaignStatus}` };
  if (input.enrollmentStatus !== 'ACTIVE') return { allowed: false, reason: `Enrollmentstatus is ${input.enrollmentStatus}` };
  if (input.emailStatus !== 'VALID' && input.emailStatus !== 'RISKY') {
    return { allowed: false, reason: `E-mailstatus is ${input.emailStatus}` };
  }
  if (!input.hasUnsubscribeLink) return { allowed: false, reason: 'Afmeldlink ontbreekt' };
  return { allowed: true };
}
