// Domein-gezondheid (§7a): SPF/DKIM/DMARC/MX-checks via DNS-lookups.
import { promises as dns } from 'dns';

export interface DnsCheckResult {
  spfOk: boolean;
  dkimOk: boolean;
  dmarcOk: boolean;
  mxOk: boolean;
  healthScore: number;
  details: Record<string, string>;
}

export function scoreHealth(r: Pick<DnsCheckResult, 'spfOk' | 'dkimOk' | 'dmarcOk' | 'mxOk'>): number {
  // SPF en DKIM zijn zwaarst (verplicht om te mogen versturen).
  let score = 0;
  if (r.spfOk) score += 35;
  if (r.dkimOk) score += 35;
  if (r.dmarcOk) score += 20;
  if (r.mxOk) score += 10;
  return score;
}

export function isSpfRecordValid(txt: string): boolean {
  return txt.startsWith('v=spf1') && (txt.includes('~all') || txt.includes('-all') || txt.includes('?all'));
}

export async function checkDomain(domain: string, dkimSelector?: string | null): Promise<DnsCheckResult> {
  const details: Record<string, string> = {};

  let spfOk = false;
  try {
    const txts = (await dns.resolveTxt(domain)).map((t) => t.join(''));
    const spf = txts.find((t) => t.startsWith('v=spf1'));
    spfOk = !!spf && isSpfRecordValid(spf);
    if (spf) details.spf = spf;
  } catch (e) {
    details.spfError = String(e);
  }

  let dkimOk = false;
  const selector = dkimSelector || 'default';
  try {
    const txts = (await dns.resolveTxt(`${selector}._domainkey.${domain}`)).map((t) => t.join(''));
    dkimOk = txts.some((t) => t.includes('v=DKIM1') || t.includes('k=rsa') || t.includes('p='));
    if (txts[0]) details.dkim = txts[0].slice(0, 120);
  } catch (e) {
    details.dkimError = String(e);
  }

  let dmarcOk = false;
  try {
    const txts = (await dns.resolveTxt(`_dmarc.${domain}`)).map((t) => t.join(''));
    dmarcOk = txts.some((t) => t.startsWith('v=DMARC1'));
    if (txts[0]) details.dmarc = txts[0];
  } catch (e) {
    details.dmarcError = String(e);
  }

  let mxOk = false;
  try {
    mxOk = (await dns.resolveMx(domain)).length > 0;
  } catch (e) {
    details.mxError = String(e);
  }

  return { spfOk, dkimOk, dmarcOk, mxOk, healthScore: scoreHealth({ spfOk, dkimOk, dmarcOk, mxOk }), details };
}

/** DNS-records die de klant moet zetten (onboarding-wizard). */
export function requiredDnsRecords(domain: string, dkimSelector: string, smtpProviderInclude: string, trackingHost: string) {
  return [
    {
      type: 'TXT',
      host: domain,
      value: `v=spf1 include:${smtpProviderInclude} ~all`,
      uitleg: 'SPF: machtigt de SMTP-provider om namens dit domein te versturen.',
    },
    {
      type: 'TXT',
      host: `${dkimSelector}._domainkey.${domain}`,
      value: '(DKIM-sleutel uit de mailprovider — Google Workspace/Microsoft 365 beheerconsole)',
      uitleg: 'DKIM: cryptografische ondertekening van uitgaande mail.',
    },
    {
      type: 'TXT',
      host: `_dmarc.${domain}`,
      value: 'v=DMARC1; p=quarantine; rua=mailto:dmarc@' + domain,
      uitleg: 'DMARC: beleid voor mail die SPF/DKIM faalt. Advies: p=quarantine.',
    },
    {
      type: 'CNAME',
      host: `link.${domain}`,
      value: trackingHost,
      uitleg: 'Tracking-domein voor open/klik-registratie en afmeldlinks.',
    },
  ];
}
