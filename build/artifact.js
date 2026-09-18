// Bouwt de webversie van de deck (build/webdeck.html) vanuit dezelfde
// contentlaag: een presentatie-viewer die als artifact gepubliceerd wordt.
'use strict';

const fs = require('fs');
const path = require('path');
const { renderSlides, BASE_CSS } = require('./template');

const ROOT = path.resolve(__dirname, '..');
const data = JSON.parse(fs.readFileSync(path.join(ROOT, 'content', 'slides.json'), 'utf8'));
const total = data.slides.length;

const html = `<title>LINK. x Techmetric3d</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Playfair+Display:ital,wght@1,600&display=swap">
<style>
${BASE_CSS}

/* ---------- viewer-chrome (bewust één donkere wereld, los van host-thema) ---------- */
html, body { height:100%; background:#07080c; }
body {
  margin:0; font-family:'Inter', 'Segoe UI', Arial, sans-serif;
  color:#e9e6dc; overflow:hidden;
}
.viewer { height:100%; display:flex; flex-direction:column; min-height:0; }

.bar {
  display:flex; align-items:center; justify-content:space-between;
  padding:14px 20px; flex:none;
}
.bar .brand { font-weight:800; font-size:20px; letter-spacing:-0.02em; color:#e9e6dc; }
.bar .brand .dot { color:#38b6ff; }
.bar .doc { font-size:13px; font-weight:500; letter-spacing:0.08em; color:#8a90a0; }

.stagewrap {
  flex:1; min-height:0; display:flex; align-items:center; justify-content:center;
  padding:0 16px;
}
.scaler { transform-origin:top left; position:relative; flex:none; }
.frames { position:relative; width:1920px; height:1080px; }
.frames .slide {
  position:absolute; top:0; left:0; opacity:0; pointer-events:none;
  transition:opacity 0.45s ease;
  border-radius:10px; box-shadow:0 20px 80px rgba(0,0,0,0.55);
}
.frames .slide.active { opacity:1; pointer-events:auto; }
@media (prefers-reduced-motion: reduce) {
  .frames .slide { transition:none; }
}

.controls {
  flex:none; display:flex; align-items:center; justify-content:center;
  gap:20px; padding:14px 16px calc(14px + env(safe-area-inset-bottom, 0px));
}
.navbtn {
  width:46px; height:46px; border-radius:50%; border:1px solid rgba(233,230,220,0.22);
  background:transparent; color:#e9e6dc; cursor:pointer;
  display:flex; align-items:center; justify-content:center; padding:0;
  transition:border-color 0.2s ease, color 0.2s ease;
}
.navbtn:hover, .navbtn:focus-visible { border-color:#38b6ff; color:#38b6ff; outline:none; }
.navbtn svg { width:20px; height:20px; }
.navbtn:disabled { opacity:0.3; cursor:default; }
.navbtn:disabled:hover { border-color:rgba(233,230,220,0.22); color:#e9e6dc; }

.dots { display:flex; gap:10px; align-items:center; }
.dotbtn {
  width:9px; height:9px; border-radius:50%; border:none; padding:0; cursor:pointer;
  background:rgba(233,230,220,0.25); transition:background 0.2s ease, transform 0.2s ease;
}
.dotbtn.active { background:#38b6ff; transform:scale(1.3); }
.dotbtn:focus-visible { outline:2px solid #38b6ff; outline-offset:3px; }

.counter {
  font-size:13px; font-weight:600; letter-spacing:0.1em; color:#8a90a0;
  font-variant-numeric:tabular-nums; min-width:52px; text-align:center;
}
.fsbtn { margin-left:4px; }

@media (max-width: 640px) {
  .bar .doc { display:none; }
  .dots { display:none; }
}
</style>
<div class="viewer" id="viewer">
  <header class="bar">
    <div class="brand">LINK<span class="dot">.</span></div>
    <div class="doc">KENNISMAKING TECHMETRIC3D</div>
  </header>
  <main class="stagewrap" id="stagewrap">
    <div class="scaler" id="scaler">
      <div class="frames" id="frames">
${renderSlides(data)}
      </div>
    </div>
  </main>
  <footer class="controls">
    <button class="navbtn" id="prev" aria-label="Vorige slide">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6"/></svg>
    </button>
    <div class="dots" id="dots"></div>
    <div class="counter" id="counter">1 / ${total}</div>
    <button class="navbtn" id="next" aria-label="Volgende slide">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m9 18 6-6-6-6"/></svg>
    </button>
    <button class="navbtn fsbtn" id="fs" aria-label="Volledig scherm">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/></svg>
    </button>
  </footer>
</div>
<script>
(function () {
  var total = ${total};
  var slides = Array.prototype.slice.call(document.querySelectorAll('.frames .slide'));
  var dotsEl = document.getElementById('dots');
  var counter = document.getElementById('counter');
  var prev = document.getElementById('prev');
  var next = document.getElementById('next');
  var fs = document.getElementById('fs');
  var viewer = document.getElementById('viewer');
  var wrap = document.getElementById('stagewrap');
  var scaler = document.getElementById('scaler');
  var current = 0;

  var fromHash = parseInt((location.hash || '').replace('#', ''), 10);
  if (fromHash >= 1 && fromHash <= total) current = fromHash - 1;

  for (var i = 0; i < total; i++) {
    var b = document.createElement('button');
    b.className = 'dotbtn';
    b.setAttribute('aria-label', 'Slide ' + (i + 1));
    (function (n) { b.addEventListener('click', function () { go(n); }); })(i);
    dotsEl.appendChild(b);
  }
  var dots = Array.prototype.slice.call(dotsEl.children);

  function go(n) {
    current = Math.max(0, Math.min(total - 1, n));
    slides.forEach(function (s, i) { s.classList.toggle('active', i === current); });
    dots.forEach(function (d, i) { d.classList.toggle('active', i === current); });
    counter.textContent = (current + 1) + ' / ' + total;
    prev.disabled = current === 0;
    next.disabled = current === total - 1;
    try { history.replaceState(null, '', '#' + (current + 1)); } catch (e) {}
  }

  function fit() {
    var padX = 32, padY = 8;
    var s = Math.min((wrap.clientWidth - padX) / 1920, (wrap.clientHeight - padY) / 1080);
    s = Math.max(s, 0.05);
    scaler.style.transform = 'scale(' + s + ')';
    scaler.style.width = 1920 * s + 'px';
    scaler.style.height = 1080 * s + 'px';
  }

  prev.addEventListener('click', function () { go(current - 1); });
  next.addEventListener('click', function () { go(current + 1); });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'ArrowRight' || e.key === ' ' || e.key === 'PageDown') { e.preventDefault(); go(current + 1); }
    if (e.key === 'ArrowLeft' || e.key === 'PageUp') { e.preventDefault(); go(current - 1); }
    if (e.key === 'Home') { e.preventDefault(); go(0); }
    if (e.key === 'End') { e.preventDefault(); go(total - 1); }
  });

  var touchX = null;
  wrap.addEventListener('touchstart', function (e) { touchX = e.changedTouches[0].clientX; }, { passive: true });
  wrap.addEventListener('touchend', function (e) {
    if (touchX === null) return;
    var dx = e.changedTouches[0].clientX - touchX;
    if (Math.abs(dx) > 40) go(current + (dx < 0 ? 1 : -1));
    touchX = null;
  }, { passive: true });

  if (viewer.requestFullscreen) {
    fs.addEventListener('click', function () {
      if (document.fullscreenElement) document.exitFullscreen();
      else viewer.requestFullscreen();
    });
  } else {
    fs.hidden = true;
  }

  window.addEventListener('resize', fit);
  document.addEventListener('fullscreenchange', fit);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(fit);
  fit();
  go(current);
})();
</script>
`;

const out = path.join(ROOT, 'build', 'webdeck.html');
fs.writeFileSync(out, html);
console.log('Webdeck geschreven:', out, Math.round(html.length / 1024) + ' KB');
