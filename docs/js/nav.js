(() => {
  const el = document.getElementById("nav-placeholder");
  if (!el) return;

  fetch("nav.html")
    .then(r => {
      if (!r.ok) throw new Error("nav.html not found");
      return r.text();
    })
    .then(html => {
      el.innerHTML = html;

      // Active state — highlight current page
      const page = location.pathname.split('/').pop().replace('.html', '') || 'index';
      el.querySelectorAll('a[data-page]').forEach(a => {
        if (a.dataset.page === page) {
          a.classList.add('active');
          const parent = a.closest('.nav-dropdown');
          if (parent) parent.querySelector('.nav-dropdown-toggle').classList.add('active');
        }
      });

      // Clock — runs after nav.html is injected
      const tzSel   = document.getElementById('tz-select');
      const clockEl = document.getElementById('live-clock');
      tzSel.value = localStorage.getItem('edgelytics_tz') || 'America/New_York';

      function tick() {
        const tz    = tzSel.value;
        const label = tzSel.options[tzSel.selectedIndex].text;
        const now   = new Date();
        const t = now.toLocaleTimeString('en-US', { timeZone: tz, hour12: false });
        const d = now.toLocaleDateString('en-US', { timeZone: tz, weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });
        clockEl.textContent = `${label}  ${t}   ${d}`;
      }

      tzSel.addEventListener('change', () => {
        localStorage.setItem('edgelytics_tz', tzSel.value);
        tick();
      });

      tick();
      setInterval(tick, 1000);
    })
    .catch(() => { el.innerHTML = ""; });
})();
