/* LINK. | linkgrp.nl
 * Alles leest uit window.LINK (data/site.js). Geen libraries, geen build.
 */
(() => {
  "use strict";
  const D = window.LINK;
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const page = (location.pathname.split("/").pop() || "index.html").replace(/^$/, "index.html");
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const arrow = '<svg class="arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>';
  const ico = {
    mail: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="3"/><path d="m4 7 8 6 8-6"/></svg>',
    phone: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2"/></svg>',
    pin: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M12 21s-7-6.2-7-12a7 7 0 0 1 14 0c0 5.8-7 12-7 12Z"/><circle cx="12" cy="9" r="2.5"/></svg>',
    web: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/></svg>'
  };
  const C = D.contact;

  /* ---------- Header + mobiel menu ---------- */
  const navLinks = D.nav.map((n) => `<a href="${n.href}"${n.href === page ? ' aria-current="page"' : ""}>${esc(n.label)}</a>`).join("");
  const portal = C.portalUrl ? `<a class="portal-link" href="${esc(C.portalUrl)}">Klantportaal</a>` : "";
  const header = document.createElement("header");
  header.className = "site-header";
  header.innerHTML = `
    <div class="wrap">
      <a class="logo" href="index.html" aria-label="LINK. home"><img src="assets/img/logo-zwart.png" alt="LINK." width="420" height="131"></a>
      <nav class="nav" aria-label="Hoofdmenu">${navLinks}</nav>
      <div class="nav-cta">${portal}<a class="btn" href="contact.html">Kop koffie? ${arrow}</a>
        <button class="burger" aria-label="Menu openen" aria-expanded="false" aria-controls="mm"><span></span><span></span></button>
      </div>
    </div>`;
  const mm = document.createElement("div");
  mm.className = "mobile-menu"; mm.id = "mm";
  mm.innerHTML = `<nav aria-label="Mobiel menu">${navLinks}${C.portalUrl ? `<a href="${esc(C.portalUrl)}">Klantportaal</a>` : ""}</nav>
    <div class="mm-meta"><a href="mailto:${C.email}">${C.email}</a><a href="tel:${C.phoneHref}">${C.phone}</a></div>`;
  document.body.prepend(mm);
  document.body.prepend(header);

  const burger = $(".burger", header);
  burger.addEventListener("click", () => {
    const open = document.documentElement.classList.toggle("menu-open");
    burger.setAttribute("aria-expanded", open);
    burger.setAttribute("aria-label", open ? "Menu sluiten" : "Menu openen");
  });
  $$("a", mm).forEach((a) => a.addEventListener("click", () => document.documentElement.classList.remove("menu-open")));
  addEventListener("keydown", (e) => { if (e.key === "Escape") document.documentElement.classList.remove("menu-open"); });

  let lastY = 0;
  const onScroll = () => {
    const y = scrollY;
    header.classList.toggle("is-scrolled", y > 20);
    header.classList.toggle("is-hidden", y > 400 && y > lastY && !document.documentElement.classList.contains("menu-open"));
    lastY = y;
  };
  addEventListener("scroll", onScroll, { passive: true }); onScroll();

  /* ---------- Footer ---------- */
  const footer = document.createElement("footer");
  footer.className = "site-footer";
  footer.innerHTML = `
    <div class="wrap">
      <div class="top">
        <div><img src="assets/img/logo-wit.png" alt="LINK." width="420" height="131" loading="lazy"><p class="tag">${esc(D.brand.tagline)}</p></div>
        <div><h4>Menu</h4><ul>${D.nav.map((n) => `<li><a href="${n.href}">${esc(n.label)}</a></li>`).join("")}${C.portalUrl ? `<li><a href="${esc(C.portalUrl)}">Klantportaal</a></li>` : ""}</ul></div>
        <div><h4>Contact</h4><ul>
          <li><a href="mailto:${C.email}">${C.email}</a></li>
          <li><a href="tel:${C.phoneHref}">${C.phone}</a></li>
          <li>${esc(C.region)}</li></ul></div>
      </div>
      <div class="giant" aria-hidden="true">LINK<span>.</span></div>
      <div class="bottom"><span>© ${new Date().getFullYear()} LINK. Alle rechten voorbehouden.</span><span>Jouw succes is ons succes.</span></div>
    </div>`;
  document.body.append(footer);

  /* ---------- Data-bindings (contactgegevens overal gelijk) ---------- */
  $$("[data-c]").forEach((el) => {
    const k = el.dataset.c;
    if (k === "email") { el.textContent = C.email; if (el.tagName === "A") el.href = `mailto:${C.email}`; }
    if (k === "phone") { el.textContent = C.phone; if (el.tagName === "A") el.href = `tel:${C.phoneHref}`; }
    if (k === "region") el.textContent = C.region;
  });
  $$("[data-details]").forEach((ul) => {
    ul.innerHTML = `
      <li><a href="mailto:${C.email}">${ico.mail}${C.email}</a></li>
      <li><a href="tel:${C.phoneHref}">${ico.phone}${C.phone}</a></li>
      <li><span>${ico.pin}${esc(C.region)}</span></li>`;
  });

  /* ---------- Foto's (allemaal uit D.photos) ---------- */
  const photoAttrs = (key, sizes = "(min-width: 960px) 50vw, 100vw") => {
    const p = D.photos && D.photos[key];
    if (!p || !p.src) return null;
    const srcset = p.widths.map((w) => `${p.src}-${w}.jpg ${w}w`).join(", ");
    return { src: `${p.src}-${p.widths[p.widths.length - 1]}.jpg`, srcset, sizes, alt: p.alt };
  };
  const imgTag = (key, extra = "") => {
    const a = photoAttrs(key);
    return a ? `<img src="${a.src}" srcset="${a.srcset}" sizes="${a.sizes}" alt="${esc(a.alt)}" loading="lazy" decoding="async"${extra}>` : "";
  };

  /* ---------- Oprichter ---------- */
  const F = D.founder;
  $$("[data-founder]").forEach((box) => {
    const img = imgTag(box.dataset.founder || "bellen");
    box.innerHTML = `
      ${img ? `<figure class="founder-photo reveal">${img}<figcaption><b></b>${esc(F.name)} · ${esc(F.role)}</figcaption></figure>` : ""}
      <div class="founder-body reveal" style="--d:.12s">
        <blockquote>${esc(F.quote)}</blockquote>
        <p class="founder-sign"><strong>${esc(F.name)}<span class="dot">.</span></strong><span>${esc(F.role)}</span></p>
      </div>`;
  });

  $$("img[data-photo]").forEach((img) => {
    const a = photoAttrs(img.dataset.photo, img.getAttribute("sizes") || undefined);
    const wrap = img.closest("[data-photo-wrap]") || img;
    if (!a) { wrap.remove(); return; }
    img.srcset = a.srcset; img.sizes = a.sizes; img.src = a.src; img.alt = a.alt;
    img.decoding = "async";
    const host = img.closest("[data-photo-host]");
    if (host) host.classList.add("has-photo");
  });
  $$("[data-founder-name]").forEach((el) => (el.textContent = F.firstName));

  /* ---------- Stappen ---------- */
  $$("[data-steps]").forEach((ol) => {
    ol.innerHTML = '<span class="progress" aria-hidden="true"></span>' +
      D.steps.map((s, i) => `<li><span class="n">${String(i + 1).padStart(2, "0")}</span><p>${esc(s)}</p></li>`).join("");
    const bar = $(".progress", ol), items = $$("li", ol);
    const tick = () => {
      const mid = innerHeight * 0.6;
      let last = -1;
      items.forEach((li, i) => { const on = li.getBoundingClientRect().top < mid; li.classList.toggle("on", on); if (on) last = i; });
      const top = items[0].offsetTop + 14;
      const end = last < 0 ? top : items[last].offsetTop + 38;
      bar.style.height = Math.max(0, end - top) + "px";
    };
    if (reduced) { items.forEach((li) => li.classList.add("on")); bar.style.height = "calc(100% - 28px)"; }
    else { addEventListener("scroll", tick, { passive: true }); addEventListener("resize", tick); tick(); }
  });

  /* ---------- Funnel (identiek aan funnel.py) ---------- */
  const funnel = (rows) => {
    const uniq = (codes) => new Set(rows.filter((r) => codes.includes(r.code)).map((r) => r.bedrijf)).size;
    return {
      pogingen: rows.length,
      gesproken: uniq(D.funnel.spoken),
      warm: uniq(D.funnel.warm),
      afspraak: uniq([100]),
      overdracht: uniq([101]),
      terugbel: uniq([500]),
      geenInt: rows.filter((r) => [200, 201, 202].includes(r.code)).length
    };
  };
  const pct = (a, b) => (b ? Math.round((100 * a) / b) : 0);
  const demoRows = () => {
    const rows = [];
    D.demoWeek.rows.forEach((g) => {
      for (let i = 0; i < g.rows; i++) rows.push({ code: g.code, bedrijf: `${g.code}-${i % g.companies}` });
    });
    return rows;
  };

  $$("[data-report]").forEach((box) => {
    const f = funnel(demoRows());
    const kpis = [
      [f.afspraak + f.overdracht, "Afspraken & overdrachten", true],
      [f.gesproken, `Bedrijven gesproken`],
      [f.terugbel, "Terugbelafspraken"],
      [f.geenInt, "Geen interesse / niet passend"]
    ];
    const rowsF = [
      ["Contactpogingen", f.pogingen, 100],
      ["Bedrijven gesproken", f.gesproken, pct(f.gesproken, f.pogingen)],
      ["Warme uitkomst", f.warm, pct(f.warm, f.pogingen)],
      ["Afspraak", f.afspraak, pct(f.afspraak, f.pogingen), true]
    ];
    box.innerHTML = `
      <div class="r-hero">
        <div><img src="assets/img/logo-wit.png" alt="" width="420" height="131"><span class="r-pill">${esc(D.demoWeek.label.toUpperCase())}</span>
        <div class="r-title">Rapportage <i>week ${D.demoWeek.week}</i></div></div>
        <div class="r-meta">Wekelijkse rapportage<br>Elke vrijdag in je portaal</div>
      </div>
      <div class="r-body">
        <div class="r-lbl">01 · Kerncijfers</div>
        <div class="kpis">${kpis.map(([n, l, hl]) => `<div class="kpi${hl ? " hl" : ""}"><b data-count="${n}">0</b><span>${esc(l)}</span></div>`).join("")}</div>
        <div class="r-lbl" style="margin-top:20px">02 · Funnel</div>
        <div class="frows">${rowsF.map(([l, v, p, blue]) => `<div class="frow${blue ? " blue" : ""}"><span>${l}</span><div class="bar"><i data-w="${Math.max(p, 2)}"></i></div><span class="v">${v}</span><span class="p">${p}%</span></div>`).join("")}</div>
        <p class="r-note">Fictieve cijfers, echt format. Percentages t.o.v. contactpogingen. Elk bedrijf telt één keer.</p>
      </div>`;
    const run = () => {
      $$(".bar i", box).forEach((i) => (i.style.width = i.dataset.w + "%"));
      $$("[data-count]", box).forEach((el) => countUp(el, +el.dataset.count));
    };
    onView(box, run);
  });

  $$("[data-codes]").forEach((box) => {
    const groups = [
      ["warm", "Warm", "telt als warm én gesproken"],
      ["gesproken", "Gesproken", "echt gesprek, geen vervolg"],
      ["vervolg", "Opvolging", "los gerapporteerd"],
      ["onbereikt", "Niet bereikt", "alleen een contactpoging"]
    ];
    box.innerHTML = groups.map(([g, t, n]) => `
      <div class="code-group"><h4>${t} <small>${n}</small></h4><div class="chips">
      ${D.resultCodes.filter((c) => c.group === g).map((c) => `<span class="chip${g === "warm" ? " warm" : ""}"><code>${c.code}</code>${esc(c.label)}</span>`).join("")}
      </div></div>`).join("");
  });

  function countUp(el, to) {
    if (reduced) { el.textContent = to; return; }
    const t0 = performance.now(), dur = 1400;
    const step = (t) => {
      const p = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - p, 4);
      el.textContent = Math.round(to * e);
      if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }

  /* ---------- Reveal ---------- */
  function onView(el, fn, opts = { threshold: 0.25 }) {
    if (!("IntersectionObserver" in window)) return fn();
    const io = new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) { fn(); io.disconnect(); } }), opts);
    io.observe(el);
  }
  const io = new IntersectionObserver((es) => es.forEach((e) => {
    if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
  }), { threshold: 0.12, rootMargin: "0px 0px -6% 0px" });
  $$(".reveal, .split-line, [data-in]").forEach((el) => io.observe(el));

  /* ---------- Manifest: woord voor woord ---------- */
  $$("[data-words]").forEach((p) => {
    p.innerHTML = p.textContent.trim().split(/\s+/).map((w) => `<span class="w">${esc(w)}</span>`).join(" ");
    const ws = $$(".w", p);
    if (reduced) return ws.forEach((w) => w.classList.add("lit"));
    const tick = () => {
      const r = p.getBoundingClientRect();
      const prog = Math.min(1, Math.max(0, (innerHeight * 0.85 - r.top) / (r.height + innerHeight * 0.35)));
      const n = Math.round(prog * ws.length);
      ws.forEach((w, i) => w.classList.toggle("lit", i < n));
    };
    addEventListener("scroll", tick, { passive: true }); tick();
  });

  /* ---------- Hero: het netwerk dat linkt ---------- */
  const cv = $("#net");
  if (cv) {
    const ctx = cv.getContext("2d");
    let W, H, dpr, nodes = [], me, links = [], mouse = { x: -999, y: -999 };
    const N = () => Math.round(Math.min(90, (W * H) / 16000));
    const resize = () => {
      dpr = Math.min(2, devicePixelRatio || 1);
      W = cv.clientWidth; H = cv.clientHeight;
      cv.width = W * dpr; cv.height = H * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const narrow = W < 900;
      const hp = $("#hero-photo"), cr = cv.getBoundingClientRect();
      if (hp && !narrow) { const r = hp.getBoundingClientRect(); me = { x: r.left - cr.left, y: r.top - cr.top + r.height * 0.22, hidden: false }; }
      else me = { x: W * 0.5, y: H + 60, hidden: true }; // mobiel: lijnen komen van onder, geen stip
      nodes = Array.from({ length: N() }, () => ({
        x: Math.random() * W, y: Math.random() * H,
        vx: (Math.random() - 0.5) * 0.12, vy: (Math.random() - 0.5) * 0.12,
        r: 1.6 + Math.random() * 1.8, won: 0
      }));
      links = [];
    };
    resize(); addEventListener("resize", resize);
    cv.parentElement.addEventListener("pointermove", (e) => { const b = cv.getBoundingClientRect(); mouse.x = e.clientX - b.left; mouse.y = e.clientY - b.top; });
    cv.parentElement.addEventListener("pointerleave", () => { mouse.x = mouse.y = -999; });

    const pick = () => {
      // Kies een prospect op afstand: de juiste afspraak, niet de dichtstbijzijnde.
      const c = nodes.filter((n) => !n.won && Math.hypot(n.x - me.x, n.y - me.y) > 160 && n.x > 20 && n.x < W - 20 && n.y > 90 && n.y < H - 40);
      if (!c.length) return;
      const n = c[(Math.random() * c.length) | 0];
      links.push({ n, t: 0 });
    };
    let last = 0;
    const draw = (t) => {
      ctx.clearRect(0, 0, W, H);
      // zachte verbindingen rond de cursor
      for (const n of nodes) {
        if (!reduced) {
          n.x += n.vx; n.y += n.vy;
          if (n.x < 0 || n.x > W) n.vx *= -1;
          if (n.y < 0 || n.y > H) n.vy *= -1;
        }
        const dm = Math.hypot(n.x - mouse.x, n.y - mouse.y);
        if (dm < 150) {
          ctx.strokeStyle = `rgba(56,182,255,${0.5 * (1 - dm / 150)})`;
          ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(mouse.x, mouse.y); ctx.lineTo(n.x, n.y); ctx.stroke();
        }
      }
      // de LINK-lijnen: jij → nieuwe klant
      for (const l of links) {
        l.t = Math.min(1, l.t + 0.012);
        const e = 1 - Math.pow(1 - l.t, 3);
        const x = me.x + (l.n.x - me.x) * e, y = me.y + (l.n.y - me.y) * e;
        ctx.strokeStyle = "rgba(0,0,0,.55)"; ctx.lineWidth = 1.2;
        ctx.beginPath(); ctx.moveTo(me.x, me.y); ctx.lineTo(x, y); ctx.stroke();
        if (l.t >= 1) l.n.won = Math.min(1, l.n.won + 0.04);
      }
      if (links.length > 7) { const old = links.shift(); old.n.won = 0; }
      for (const n of nodes) {
        const won = n.won;
        ctx.fillStyle = won ? `rgba(56,182,255,${0.4 + 0.6 * won})` : "rgba(20,24,30,.28)";
        ctx.beginPath(); ctx.arc(n.x, n.y, n.r + won * 3.5, 0, 7); ctx.fill();
        if (won) { ctx.strokeStyle = `rgba(56,182,255,${0.25 * won})`; ctx.lineWidth = 6; ctx.beginPath(); ctx.arc(n.x, n.y, n.r + 8, 0, 7); ctx.stroke(); }
      }
      // jij
      const pulse = reduced ? 0 : (Math.sin(t / 600) + 1) / 2;
      if (!me.hidden) {
        ctx.fillStyle = "rgba(56,182,255,.14)"; ctx.beginPath(); ctx.arc(me.x, me.y, 22 + pulse * 10, 0, 7); ctx.fill();
        ctx.fillStyle = "#000"; ctx.beginPath(); ctx.arc(me.x, me.y, 9, 0, 7); ctx.fill();
      }
      
      if (!reduced && t - last > 2600) { pick(); last = t; }
      if (!reduced) requestAnimationFrame(draw);
    };
    if (reduced) { for (let i = 0; i < 5; i++) pick(); links.forEach((l) => { l.t = 1; l.n.won = 1; }); draw(0); }
    else requestAnimationFrame(draw);
  }

  /* ---------- Hero live-kaart ---------- */
  const lc = $("[data-live]");
  if (lc && !reduced) {
    const items = [
      ["Kennismaking ingepland", "Installatietechniek · Zuid-Holland", "Beslisser", "Directeur-eigenaar"],
      ["Warme lead overgedragen", "Zakelijke dienstverlening · Noord-Holland", "Moment", "Na de zomer"],
      ["Kennismaking ingepland", "Maakindustrie · 50-100 medewerkers", "Beslisser", "Operationeel directeur"],
      ["Terugbelafspraak", "Horeca & kantoren · Leiden", "Reden", "Contract loopt af in Q1"]
    ];
    let i = 0;
    const els = $$(".lc-swap", lc);
    setInterval(() => {
      els.forEach((e) => e.classList.add("out"));
      setTimeout(() => {
        i = (i + 1) % items.length;
        const [a, b, c, d] = items[i];
        $(".lc-title", lc).textContent = a; $(".lc-sub", lc).textContent = b;
        $(".lc-k", lc).textContent = c; $(".lc-v", lc).textContent = d;
        els.forEach((e) => e.classList.remove("out"));
      }, 500);
    }, 4200);
  }

  /* ---------- Contactformulier ---------- */
  const form = $("#contact-form");
  if (form) {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (form.website && form.website.value) return; // honeypot
      if (!form.reportValidity()) return;
      const v = Object.fromEntries(new FormData(form));
      const box = form.closest(".form");
      const btn = $("button[type=submit]", form);
      btn.disabled = true;
      const F = C.form;
      if (F.endpoint) {
        const body = new URLSearchParams();
        Object.entries(F.fields).forEach(([k, id]) => { if (id && v[k]) body.append(id, v[k]); });
        try { await fetch(F.endpoint, { method: "POST", mode: "no-cors", body }); } catch (_) { /* no-cors geeft geen status */ }
        box.classList.add("sent");
      } else {
        const lines = [
          `Naam: ${v.naam}`, `Bedrijf: ${v.bedrijf}`, `E-mail: ${v.email}`, `Telefoon: ${v.telefoon || "-"}`, "",
          `Bij wie wil ik aan tafel zitten?`, v.tafel || "-", "", `Groeiambitie:`, v.ambitie || "-"
        ];
        location.href = `mailto:${C.email}?subject=${encodeURIComponent(`Kennismaking ${v.bedrijf || ""}`.trim())}&body=${encodeURIComponent(lines.join("\n"))}`;
        box.classList.add("sent");
      }
      btn.disabled = false;
    });
  }

  /* ---------- Cursor + magnetische knoppen ---------- */
  if (matchMedia("(hover: hover) and (pointer: fine)").matches && !reduced) {
    const cur = document.createElement("div"); cur.className = "cursor"; document.body.append(cur);
    let x = 0, y = 0, cx = 0, cy = 0;
    addEventListener("pointermove", (e) => { x = e.clientX; y = e.clientY; cur.classList.add("on"); });
    document.addEventListener("pointerleave", () => cur.classList.remove("on"));
    const loop = () => { cx += (x - cx) * 0.22; cy += (y - cy) * 0.22; cur.style.transform = `translate(${cx}px,${cy}px)`; requestAnimationFrame(loop); };
    loop();
    document.addEventListener("pointerover", (e) => cur.classList.toggle("big", !!e.target.closest("a, button, .pillar, .service")));
    $$(".btn").forEach((b) => {
      b.addEventListener("pointermove", (e) => { const r = b.getBoundingClientRect(); b.style.transform = `translate(${(e.clientX - r.left - r.width / 2) * 0.18}px, ${(e.clientY - r.top - r.height / 2) * 0.3}px)`; });
      b.addEventListener("pointerleave", () => (b.style.transform = ""));
    });
  }
})();
