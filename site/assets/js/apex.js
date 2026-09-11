/* Apex MD — chrome behaviour. Everything else on each page ships its own
   inline script from the handoff. Nothing here is required for the page to
   render: with JS off you get the full desktop nav and no drawer. */
(function () {
  'use strict';

  // ---------------------------------------------------------- mobile drawer
  var drawer = document.getElementById('nav-drawer');
  var burger = document.querySelector('[data-drawer-open]');

  if (drawer && burger) {
    var lastFocus = null;

    function openDrawer() {
      lastFocus = document.activeElement;
      drawer.hidden = false;
      document.body.classList.add('nav-open');
      burger.setAttribute('aria-expanded', 'true');
      var first = drawer.querySelector('a, button');
      if (first) first.focus();
    }

    function closeDrawer() {
      drawer.hidden = true;
      document.body.classList.remove('nav-open');
      burger.setAttribute('aria-expanded', 'false');
      if (lastFocus) lastFocus.focus();
    }

    burger.addEventListener('click', openDrawer);

    Array.prototype.forEach.call(
      drawer.querySelectorAll('[data-drawer-close]'),
      function (el) { el.addEventListener('click', closeDrawer); }
    );

    // any destination link closes the drawer behind it
    Array.prototype.forEach.call(drawer.querySelectorAll('a[href]'), function (a) {
      a.addEventListener('click', closeDrawer);
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && !drawer.hidden) closeDrawer();
    });

    // if the viewport grows back to desktop while the drawer is open, the
    // drawer's own styles stop applying — so close it rather than trapping focus
    window.addEventListener('resize', function () {
      if (!drawer.hidden && window.innerWidth > 760) closeDrawer();
    });
  }

  // ------------------------------------------------------- nav dropdowns
  // Hover opens them via CSS. This adds keyboard and touch support, which
  // hover alone cannot provide.
  var drops = document.querySelectorAll('.hdr-drop');

  Array.prototype.forEach.call(drops, function (drop) {
    var btn = drop.querySelector('.hdr-drop-btn');
    if (!btn) return;

    btn.addEventListener('click', function (e) {
      e.preventDefault();
      var open = btn.getAttribute('aria-expanded') === 'true';
      closeAll();
      btn.setAttribute('aria-expanded', open ? 'false' : 'true');
    });

    drop.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        btn.setAttribute('aria-expanded', 'false');
        btn.focus();
      }
    });
  });

  function closeAll() {
    Array.prototype.forEach.call(
      document.querySelectorAll('.hdr-drop-btn[aria-expanded="true"]'),
      function (b) { b.setAttribute('aria-expanded', 'false'); }
    );
  }

  document.addEventListener('click', function (e) {
    if (!e.target.closest || !e.target.closest('.hdr-drop')) closeAll();
  });

  // ----------------------------------------------------------- carousels
  // The GLP-1 handoff's testimonial carousel had its arrows wired by the
  // design tool's runtime. build.py turns those bindings into data hooks;
  // this scrolls the track one card per click.
  Array.prototype.forEach.call(
    document.querySelectorAll('[data-carousel-track]'),
    function (track) {
      // the arrows sit beside the track, a level or two up
      var root = track.parentElement;
      for (var i = 0; i < 3 && root &&
           !root.querySelector('[data-carousel-prev],[data-carousel-next]'); i++) {
        root = root.parentElement;
      }
      if (!root) return;

      function step(dir) {
        var card = track.firstElementChild;
        var gap = parseFloat(getComputedStyle(track).columnGap) || 0;
        var w = card ? card.getBoundingClientRect().width + gap : track.clientWidth * 0.8;
        track.scrollBy({ left: dir * w, behavior: 'smooth' });
      }

      var prev = root.querySelector('[data-carousel-prev]');
      var next = root.querySelector('[data-carousel-next]');
      if (prev) prev.addEventListener('click', function () { step(-1); });
      if (next) next.addEventListener('click', function () { step(1); });
    }
  );
})();
