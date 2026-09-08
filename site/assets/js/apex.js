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
})();
