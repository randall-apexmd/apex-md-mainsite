# _build/qa — visual checks

Not part of the build, and not deployed. These drive a real headless Chrome
over the DevTools protocol (no npm dependencies) against a local server:

    python3 -m http.server 4310 --directory site

    node _build/qa/shoot.mjs    /tmp/qa/shots  # full-page PNGs at 1440 and 390
    node _build/qa/inspect.mjs  /tmp/qa/insp   # defect scan -> insp/inspect.json
    node _build/qa/overflow.mjs /tmp/qa        # phone-width content past the edge

`inspect.mjs` walks each page a viewport at a time and reports text covered
by an unrelated element, images painted at the wrong aspect ratio, near-white
text on a near-white background, fixed bars and their heights, and CTAs with
no label. Each script scrolls the whole page first, so scroll-reveal
animations and lazy images have fired before anything is measured.

Known false positives — check these by eye rather than "fixing" them:

- the back faces of the homepage's flip cards (hidden until tapped)
- animated marquee items, which move between measure and hit-test
- collapsed FAQ answers, and Concierge's hidden newsletter modal
- Concierge's doctor and diagnostics sliders, which clip by design
- white text over a dark photo: the scan reads the page background, not
  the image (Women's "Optimization Membership" card)
- the full-page capture draws fixed bars at the viewport edge, mid-page
