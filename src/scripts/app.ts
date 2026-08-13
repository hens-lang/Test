/* LINK. — verfijnde site-interacties (nav-drawer, reveals, magnetische CTA) */

const prefersReducedMotion = window.matchMedia(
  '(prefers-reduced-motion: reduce)',
).matches;
const finePointer = window.matchMedia('(pointer: fine)').matches;

// ============== Mobiel nav-drawer ==============
function buildMobileNav() {
  const navInner = document.querySelector<HTMLElement>('.site-nav');
  const links = document.querySelector<HTMLElement>('.site-links');
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

  const right = document.querySelector('.site-right');
  if (right) {
    const div = document.createElement('div');
    div.className = 'nav-drawer-div';
    inner.appendChild(div);
    right.querySelectorAll('a').forEach((a) => {
      const item = document.createElement('a');
      item.href = a.getAttribute('href') || '#';
      item.className = a.classList.contains('site-cta') ? 'dr-cta' : 'dr-login';
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
  const nav = document.querySelector<HTMLElement>('.site-nav');
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

// ============== Zachte reveals ==============
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
    { rootMargin: '0px 0px -60px 0px', threshold: 0.1 },
  );
  els.forEach((el) => obs.observe(el));
}

// ============== Ingetogen magnetische elementen ==============
function magnetic() {
  if (!finePointer || prefersReducedMotion) return;
  document.querySelectorAll<HTMLElement>('[data-magnetic]').forEach((el) => {
    el.addEventListener('mousemove', (e) => {
      const r = el.getBoundingClientRect();
      const dx = (e.clientX - (r.left + r.width / 2)) * 0.18;
      const dy = (e.clientY - (r.top + r.height / 2)) * 0.18;
      el.style.transform = `translate(${dx}px, ${dy}px)`;
    });
    el.addEventListener('mouseleave', () => {
      el.style.transform = '';
    });
  });
}

buildMobileNav();
navScroll();
reveal();
magnetic();
