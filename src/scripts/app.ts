/* LINK. — gedeelde site-interacties (nav-drawer, scroll, reveal, parallax) */

const prefersReducedMotion = window.matchMedia(
  '(prefers-reduced-motion: reduce)',
).matches;

// ============== Mobiel nav-drawer ==============
function buildMobileNav() {
  const navInner = document.querySelector<HTMLElement>('.nav .nav-inner');
  const links = document.querySelector<HTMLElement>('.nav .nav-links');
  if (!navInner || !links || document.querySelector('.nav-burger')) return;

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

  links.querySelectorAll('a').forEach((a) => {
    const item = document.createElement('a');
    item.href = a.getAttribute('href') || '#';
    item.textContent = a.textContent;
    if (a.classList.contains('active')) item.classList.add('active');
    inner.appendChild(item);
  });

  const right = document.querySelector('.nav .nav-right');
  if (right) {
    const div = document.createElement('div');
    div.className = 'nav-drawer-div';
    inner.appendChild(div);
    right.querySelectorAll('a').forEach((a) => {
      const item = document.createElement('a');
      item.href = a.getAttribute('href') || '#';
      item.className = a.classList.contains('nav-cta') ? 'dr-cta' : 'dr-login';
      if (a.getAttribute('target')) item.target = a.getAttribute('target')!;
      item.rel = a.getAttribute('rel') || '';
      item.textContent = (a.textContent || '').trim();
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

// ============== Nav verbergen bij scrollen omlaag + schaduw ==============
function navScroll() {
  const nav = document.querySelector<HTMLElement>('.nav');
  if (!nav) return;
  let lastY = window.scrollY;
  window.addEventListener(
    'scroll',
    () => {
      const y = window.scrollY;
      nav.classList.toggle('scrolled', y > 20);
      if (y > 200 && y > lastY + 4) nav.classList.add('hidden');
      else if (y < lastY - 4 || y < 100) nav.classList.remove('hidden');
      lastY = y;
    },
    { passive: true },
  );
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

// ============== Parallax ==============
function parallax() {
  if (prefersReducedMotion) return;
  const parallaxEls =
    document.querySelectorAll<HTMLElement>('[data-parallax]');
  if (!parallaxEls.length) return;
  let ticking = false;
  const update = () => {
    parallaxEls.forEach((el) => {
      const speed = parseFloat(el.dataset.parallax || '0.2') || 0.2;
      const rect = el.getBoundingClientRect();
      const center = rect.top + rect.height / 2;
      const off = (window.innerHeight / 2 - center) * speed;
      el.style.transform = `translate3d(0, ${off}px, 0)`;
    });
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

buildMobileNav();
navScroll();
reveal();
parallax();
