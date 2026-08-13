/**
 * Centrale siteconfiguratie voor LINK.
 * Vaste gegevens, navigatie en externe diensten op één plek.
 */

export const site = {
  name: 'LINK.',
  legalName: 'LINK.',
  url: 'https://www.linkgrp.nl',
  locale: 'nl_NL',
  lang: 'nl',
  description:
    'LINK. brengt B2B-bedrijven persoonlijk aan tafel bij nieuwe klanten. Telefonische acquisitie door ervaren mensen, maandelijks opzegbaar.',

  contact: {
    email: 'info@linkgrp.nl',
    phoneDisplay: '(0172) 27 10 08',
    phoneHref: '+31172271008',
    street: 'Flemingweg 8',
    postalCode: '2408 AV',
    city: 'Alphen aan den Rijn',
    country: 'NL',
    mapsUrl: 'https://maps.google.com/?q=Flemingweg+8+2408AV+Alphen+aan+den+Rijn',
  },

  portal: {
    url: 'https://partnerportaal.linkgrp.nl/',
    label: 'Inloggen',
  },

  /**
   * Apollo website tracker. Laadt PAS na cookie-consent (zie CookieConsent.astro).
   */
  apollo: {
    appId: '695040eaae2147001516e8ad',
  },

  /**
   * Contactformulier-backend.
   * Web3Forms (https://web3forms.com) — gratis, geen server nodig, met
   * ingebouwde spamprotectie (honeypot) en autoresponder.
   * Vul de access key in via de env-var PUBLIC_WEB3FORMS_KEY (zie README-nieuw.md).
   */
  forms: {
    web3formsKey: import.meta.env.PUBLIC_WEB3FORMS_KEY ?? '',
    endpoint: 'https://api.web3forms.com/submit',
  },
} as const;

export const nav: { label: string; href: string }[] = [
  { label: 'Home', href: '/' },
  { label: 'Aanpak', href: '/aanpak' },
  { label: 'Wat we doen', href: '/diensten' },
  { label: 'Ons verhaal', href: '/verhaal' },
  { label: 'Contact', href: '/contact' },
];

export type SEO = {
  title: string;
  description: string;
  path: string;
  ogImage?: string;
};
