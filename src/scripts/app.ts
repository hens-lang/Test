/* LINK. — editorial site-interacties (nav-drawer, thread, reveal, index) */

const prefersReducedMotion = window.matchMedia(
  '(prefers-reduced-motion: reduce)',
).matches;

// ============== Mobiel nav-drawer ==============
function buildMobileNav() {
  const navInner = document.querySelector<HTMLElement>('.enav');
  const links = document.querySelector<HTMLElement>('.enav-links');
  if (!navInner || document.querySelector('.nav-burger')) return;

  const burger = document.createElement('button');
  burger.className = 'nav-burger';
  burger.setAttribute('aria-label', 'Menu openen');
  burger.setAttribute('aria-expanded', 'false');
  burger.innerHTML = '<span></span><span></span><span></span>';
  navInner.appendChild(burger);

  const drawer = document.createElement('div');
  drawer.className = 'nav-drawer';
  const inner = document.createElement('nav');
  inner.className = 'nav-drawer-inner';
  inner.setAttribute('aria-label', 'Mobiel menu');

  links?.querySelectorAll('a').forEach((a) => {
    const item = document.createElement('a');
    item.href = a.getAttribute('href') || '#';
    item.textContent = a.textContent;
    if (a.classList.contains('active')) item.classList.add('active');
    inner.appendChild(item);
  });

  const right = document.querySelector('.enav-right');
  if (right) {
    const div = document.createElement('div');
    div.className = 'nav-drawer-div';
    inner.appendChild(div);
    right.querySelectorAll('a').forEach((a) => {
      const item = document.createElement('a');
      item.href = a.getAttribute('href') || '#';
      item.className = a.classList.contains('enav-cta') ? 'dr-cta' : 'dr-login';
      if (a.getAttribute('target')) item.target = a.getAttribute('target')!;
      item.rel = a.getAttribute('rel') || '';
      item.textContent = (a.textContent || '').replace('→', '').trim();
      inner.appendChild(item);
    });
  }
  drawer.appendChild(inner);
  document.body.appendChild(drawer);

  function setOpen(open: boolean) {
    drawer.classList.toggle('open', open);
    burger.classList.toggle('open', open);
    burger.setAttribute('aria-expanded', String(open));
    burger.setAttribute('aria-label', open ? 'Menu sluiten' : 'Menu openen');
    document.body.style.overflow = open ? 'hidden' : '';
  }
  burger.addEventListener('click', () =>
    setOpen(!drawer.classList.contains('open')),
  );
  drawer.addEventListener('click', (e) => {
    if (e.target === drawer) setOpen(false);
  });
  inner
    .querySelectorAll('a')
    .forEach((a) => a.addEventListener('click', () => setOpen(false)));
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') setOpen(false);
  });
}

// ============== Nav verbergen bij scrollen omlaag ==============
function navScroll() {
  const nav = document.querySelector<HTMLElement>('.enav');
  if (!nav) return;
  let lastY = window.scrollY;
  window.addEventListener(
    'scroll',
    () => {
      const y = window.scrollY;
      if (y > 240 && y > lastY + 4) nav.classList.add('hidden');
      else if (y < lastY - 4 || y < 120) nav.classList.remove('hidden');
      lastY = y;
    },
    { passive: true },
  );
}

// ============== Thread: voortgang tekenen op scroll ==============
function thread() {
  const el = document.querySelector<HTMLElement>('.thread');
  if (!el) return;
  if (prefersReducedMotion) {
    el.style.setProperty('--p', '1');
    return;
  }
  let ticking = false;
  const update = () => {
    const h = document.body.scrollHeight - window.innerHeight;
    const p = Math.min(1, Math.max(0, window.scrollY / (h || 1)));
    el.style.setProperty('--p', String(p));
    ticking = false;
  };
  window.addEventListener(
    'scroll',
    () => {
      if (!ticking) {
        requestAnimationFrame(update);
        ticking = true;
      }
    },
    { passive: true },
  );
  update();
}

// ============== Hoofdstuk-index: actieve markeren ==============
function chapterIndex() {
  const links = document.querySelectorAll<HTMLElement>('.chapter-index a');
  if (!links.length) return;
  const map = new Map<string, HTMLElement>();
  links.forEach((a) => {
    const id = a.getAttribute('href')?.slice(1);
    if (id) map.set(id, a);
  });
  const targets = Array.from(map.keys())
    .map((id) => document.getElementById(id))
    .filter(Boolean) as HTMLElement[];
  if (!targets.length) return;
  const obs = new IntersectionObserver(
    (entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) {
          links.forEach((l) => l.classList.remove('active'));
          map.get(e.target.id)?.classList.add('active');
        }
      });
    },
    { rootMargin: '-45% 0px -50% 0px' },
  );
  targets.forEach((t) => obs.observe(t));
}

// ============== Reveal-on-scroll ==============
function reveal() {
  const els = document.querySelectorAll('.reveal, .reveal-stagger');
  if (prefersReducedMotion) {
    els.forEach((el) => el.classList.add('in'));
    return;
  }
  const obs = new IntersectionObserver(
    (entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) {
          e.target.classList.add('in');
          obs.unobserve(e.target);
        }
      });
    },
    { rootMargin: '0px 0px -80px 0px', threshold: 0.05 },
  );
  els.forEach((el) => obs.observe(el));
}

buildMobileNav();
navScroll();
thread();
chapterIndex();
reveal();
