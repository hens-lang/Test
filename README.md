# LINK. Outreach

Productiewaardig e-mailcampagneplatform van **LINK.** — multi-tenant, deliverability-first, met AI-ondersteunde personalisatie waarbij **altijd een mens beslist**.

## Kernprincipes

1. **Deliverability boven alles** — warm-up, caps, spreiding, validatie, suppressie en stop-regels zitten hard in de backend (verzendjob), niet alleen in de UI.
2. **Personalisatie per prospect** — AI-openers (of regelgebaseerd zonder API-key) met menselijke reviewstap.
3. **Eén datamodel, één waarheid** — generieke `Activity`-tabel, voorbereid op Steam Connect (CALL_*) en Zoho.
4. **Techniek onzichtbaar** — team en klant zien een simpele Nederlandse interface.
5. **Mens beslist, AI stelt voor** — geen enkele AI-output verlaat het systeem zonder goedkeuring.

> **Kernasset:** de geanonimiseerde `TemplateStat`-bibliotheek (welke onderwerpsregels/openers per branche werken) is tenant-overstijgende prestatiedata en hoort in **elke backup**.

## Snel starten (lokaal)

```bash
cp .env.example .env          # vul minimaal DATABASE_URL, SESSION_SECRET, ENCRYPTION_KEY
docker compose up -d postgres # of eigen Postgres
npx prisma migrate deploy     # schema
npm install
npm run db:seed               # demodata
npm run dev                   # app op :3000
npm run worker                # jobs (tweede terminal)
```

Of alles in één keer met Docker:

```bash
docker compose up --build
docker compose exec app npm run db:seed
```

**Demo-logins** (wachtwoord `demo1234`):

| Login | Rol |
|---|---|
| `admin@linkgrp.nl` | ADMIN (LINK.) |
| `team@linkgrp.nl` | MANAGER (LINK.-teamlid) |
| `klant@demoklant.nl` | CLIENT — campagne-abonnement |
| `klant@demodata.nl` | CLIENT — data-abonnement (DATA_ONLY) |

## Verzendmodus

- `SEND_MODE=demo` (default): mails worden **niet** verstuurd, wel volledig gerenderd en gelogd — alle flows werken end-to-end.
- `SEND_MODE=live`: echt versturen via SMTP per mailbox. Vereist geldige SPF+DKIM op het domein (hard afgedwongen in de verzendjob).

Zonder `ANTHROPIC_API_KEY` valt elke AI-functie terug op regelgebaseerde alternatieven (openers, classificatie, referral-extractie, conceptantwoorden).

## Architectuur

- **Next.js 14 (App Router, TypeScript)** — UI + server actions, alles Nederlands.
- **PostgreSQL + Prisma** — datamodel in `prisma/schema.prisma`.
- **pg-boss** — jobs/cron op dezelfde Postgres (bewust geen Redis): verzendplanner, verzendjob (met harde verzendpoort), warm-up, DNS-checks (6-uurlijks), IMAP-poll (2 min), TemplateStat-aggregatie, week-/maandrapportages, DataHealthRuns, AVG-retentie.
- **nodemailer / imapflow** — versturen en ontvangen per mailbox (Google Workspace / M365 app-passwords). Credentials AES-256-GCM-versleuteld (`ENCRYPTION_KEY`).
- **Multi-tenancy** — `tenantDb(tenantId)` (Prisma-extensie) injecteert tenantId in álle queries; bewezen met tests.
- **Gedeelde query-laag** — `src/core/stats.ts` voedt dashboard én rapportages: geen dubbele berekeningen.

Prompts staan bewust in makkelijk aanpasbare bestanden: `src/personalization/prompts.ts` en `src/reply-assistant/prompts.ts`.

## Deliverability-regels (hard afgedwongen)

- Nieuwe mailbox start in warm-up: week 1: 10/dag → 20 → 35 → 50; bovengrens 100 alleen door ADMIN.
- Verzendvenster (default 08:30–17:00 ma–vr, Europe/Amsterdam), random jitter 90–240 s per mailbox.
- Zonder geldige SPF+DKIM verstuurt een domein **niets**.
- Elke mail: `List-Unsubscribe` (mailto + https, RFC 8058 one-click) + afmeldlink + fysiek afzenderadres in de footer; plain-text-first, max 1 tracking-pixel (per campagne uitschakelbaar).
- Guardrails: campagne-bounce-rate >3%/laatste 100 → campagne PAUSED; mailbox >5% bounces/dag of 3 SMTP-fouten op rij → mailbox PAUSED; ≥2 spamklachten → domein PAUSED; hard bounce → globale suppressie; unsubscribe → tenant-suppressie + alle enrollments direct gestopt.
- Alle tellers (sentToday e.d.) staan in de database: caps overleven een herstart.

## Tests

```bash
npm run test        # Vitest: planner/caps, warm-up, guardrails+verzendpoort, suppressie,
                    # template-rendering, tenant-isolatie, referral-extractie, anonimisering, lint
npm run typecheck
npm run lint
```

## Deploy op een EU-VPS (bijv. Hetzner)

1. VPS met Docker + Docker Compose (EU-regio i.v.m. AVG).
2. Repo klonen, `.env` vullen: sterke `SESSION_SECRET`, `ENCRYPTION_KEY` (`openssl rand -hex 32`), `APP_URL=https://outreach.linkgrp.nl`, `SEND_MODE=demo` (eerst!).
3. `docker compose up -d --build` en een reverse proxy (Caddy/Traefik/nginx) met TLS voor poort 3000.
4. Database-backups inplannen (`pg_dump`, dagelijks) — inclusief de TemplateStat-bibliotheek.

## Go-live-checklist (per klant)

1. **Verzenddomein registreren** — bij voorkeur een apart domein (bijv. `mail.klant.nl`), nooit het hoofddomein.
2. **Domein toevoegen** in *Beheer → Domeinen & mailboxen*; de wizard toont de exacte DNS-records (SPF, DKIM-selector, DMARC `p=quarantine`, tracking-CNAME).
3. **DNS zetten** en op "Check nu" klikken tot SPF/DKIM/DMARC/MX groen zijn (automatische hercontrole elke 6 uur).
4. **Mailboxen aanmaken** (Google Workspace/M365), app-passwords genereren en de mailbox toevoegen — warm-up start automatisch op 10/dag.
5. **Tenant inrichten**: fysiek afzenderadres (verplicht), tone-of-voice-profiel, rapportage-ontvangers, plan/abonnement koppelen.
6. **Prospects importeren** (CSV, dry-run eerst) en validatie laten draaien; alleen VALID (evt. RISKY na expliciete keuze) is enrollbaar.
7. **Campagne bouwen**: sequence met {{variabelen}} en {{opener}}, spam-lint moet blocker-vrij zijn; preview op 5 echte prospects bekijken.
8. **Eerste campagne volledig in demo reviewen**: enroll → openers goedkeuren → gesimuleerde verzending → reply-flow testen.
9. **Pas daarna** `SEND_MODE=live` zetten — en de eerste week dagelijks het monitoring-dashboard checken (bounce-rate, warm-up, ampelkleuren).

## AVG

- Data-export per tenant: `/api/export/<tenantId>` (CSV, alleen staff).
- Recht op vergetelheid: `anonymizeContact()` hard-delete + anonimiseert Messages/Activities/Referrals.
- Retentiejob: prospects zonder activiteit > 18 maanden worden wekelijks geanonimiseerd.
- Geen persoonsgegevens in logs (pino met redactie); TemplateStat bevat uitsluitend geanonimiseerde templates (getest).
