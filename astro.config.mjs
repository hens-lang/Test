// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

// De canonieke basis-URL. Gebruikt voor sitemap, canonical en OG-tags.
const SITE = 'https://www.linkgrp.nl';

// https://astro.build/config
export default defineConfig({
  site: SITE,
  // Statische output: overal te hosten. Het contactformulier gebruikt een
  // externe form-backend (zie src/lib/site.ts en README-nieuw.md).
  output: 'static',
  trailingSlash: 'never',
  build: {
    // Extensieloze URL's zoals de oude .htaccess (/aanpak i.p.v. /aanpak.html)
    format: 'file',
  },
  integrations: [
    sitemap({
      i18n: undefined,
      filter: (page) => !page.includes('/bedankt'),
    }),
  ],
  image: {
    // Sharp voor beeldoptimalisatie (WebP/AVIF) via <Image />.
    responsiveStyles: true,
  },
});
