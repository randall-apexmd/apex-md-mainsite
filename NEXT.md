# Where we left off — 2026-09-09

Live preview: **https://apex-md-mainsite-kz2h.vercel.app**
All seven pages build, deploy and render at desktop and mobile. Repo is clean
and pushed.

## Visual scrub — 2026-09-11

Every page was screenshotted full-length at 1440px and 390px and run through
an automated defect scan (covered text, stretched images, invisible text,
overflow). The tools are in `_build/qa/`; rerun them after any layout change.

**Fixed.** All of these were bugs in `_build/`, not in the designs:

- GLP-1 and Apex AI had lost their accent colour. The canvas exports use
  `{{ accent }}` as a live template binding (62 times on Apex AI), and the
  build deleted those tokens instead of resolving them — blank buttons,
  icons that drew nothing, a whole section white on white. They now resolve
  from each file's declared defaults. The GLP-1 carousel arrows are wired.
- 28 images were drawn at the wrong shape. The width/height attributes added
  in the performance pass let the height win wherever a design sizes an
  image by width alone. Fixed with `height:auto` in apex.css.
- Phone layouts:
  - Bullet dots and check icons had dropped onto their own line above their
    text. Flex rows now only wrap when they hold a link, a button, or three
    or more items.
  - Genetics ran 113px past the screen edge.
  - Content was covered by images on Women's (twice), on Apex AI, and in the
    Genetics comparison table.
  - The GLP-1 timeline badges sat on top of their headings.
  - Logo strips and the homepage CTA card were clipped instead of wrapping.
  - The Men's and Women's bottom bar was 164px tall, a fifth of the screen.
    It is now 69px.
  - Concierge's phone header showed the desktop CTA.

**Open, and not a build problem.** Each needs an asset or a decision:

- **Genetics has 4 grey image placeholders** left in the handoff: "Man
  reviewing results", "Member reading results on a tablet", "Member checking
  her action steps on her phone", and "Shield and padlock".
- **Men's and Women's carry a second header strip** ("HSA / FSA eligible · no
  membership required · Patient Login") under the shared header. It
  duplicates Patient Login and is a tall two-line block on phones. Merge the
  HSA line into the page, or drop the strip.
- **GLP-1's Tirzepatide comparison table is an image** (`tirz-comparison`).
  On a phone it shrinks to ~350px and cannot be read. It needs to be an HTML
  table or have a phone-specific image.
- **Apex AI's hero is one baked image.** On a phone its headline renders at
  about 12px. It needs a phone hero, or a text hero over the art.
- **Testosterone's "wrong form of testosterone" card** has its copy baked into
  the photo, and the phone crop cuts it off.
- **The "Apex specialists … have been used by" strip** (homepage,
  Testosterone, Men's, Women's) is a single image of about 12 logos. At
  phone width each logo is ~15px.
- **Concierge lays out 2 doctor cards in a 3-column grid**, leaving an empty
  third slot on desktop.
- **Phone pages are long.** Women's is 41,676px on a phone, because every
  card grid stacks one card per row. Symptom and benefit cards could go two
  across on phones. This is a design call, not a defect.

## Pick up here

### 1. The eleven dead nav links

`/concierge` is now built. The header and footer still link eleven routes
that do not exist:

    /about-us   /advanced-diagnostics   /bloodwork
    /contact    /hormone-therapy        /microdosing /partner
    /peptides   /privacy-policy         /supplements /terms-and-conditions

**Do not start these from scratch.** There is far more source material on disk
than the seven handoffs — this was missed on the first pass and is the main
reason to read this file before writing anything:

    ~/Desktop/Claude/Web Design/
      SPENGA Apex MD Site/            12 pages, plain .html
      DF360 Apex MD Site/             12 pages, plain .html
      # Vibe Fitness Website Redesign/ 14 pages, .dc.html + _SiteHeader/_SiteFooter
      EoS Apex MD Site/

SPENGA and DF360 are partner-branded builds of the *same* Apex MD site, and
between them they already cover most of the gap:

    about.html          -> /about-us
    contact.html        -> /contact
    bloodwork.html      -> /bloodwork
    hormones.html       -> /hormone-therapy
    glp-1-microdosing   -> /microdosing
    sermorelin.html     -> /peptides (partial — one product)
    nad.html            -> /peptides (partial — one product)
    faq.html            -> new, not currently in the nav
    how-it-works.html   -> new, not currently in the nav

They will need the same treatment the seven got: strip partner branding,
normalise onto Archivo + `#d30704`, swap in the shared chrome from
`_build/parts/`, and route CTAs through the `CTA` table in `_build/build.py`.
Adding a page is a one-line entry in `PAGES` plus its `_src/` folder.

Still genuinely missing after that: `/concierge`, `/supplements`,
`/advanced-diagnostics`, `/partner`. Those exist only as copy on the live
WordPress site (see the word counts below).

### 2. Legal pages — Blake asked for these VERBATIM

Both must be lifted word-for-word from the live site. Do not paraphrase,
summarise, or re-order. They are approved legal copy.

**Privacy Policy** — 6,842 words, sits in the static HTML inside an
`elementor-widget-text-editor` div. Extractable with plain HTTP; the working
extractor is in the transcript. Begins:

> Privacy Policy — Apex MD — Last updated: April 10, 2026
> IF YOU ARE EXPERIENCING A MEDICAL EMERGENCY, CALL 911 IMMEDIATELY.

**Terms of Service** — 13,152 words, and **not** in the served HTML. The page
returns only 63 words of body text; the content is rendered client-side, so
`curl` gets nothing usable. It has to be pulled from a real browser
(`document.body.innerText` after load). Begins:

> Apex MD — Terms of Service — Last updated: April 10, 2026
> APEX MD IS CONTEMPLATED FOR SPECIFIC NON-EMERGENCY MEDICAL CONDITIONS…

Both want a plain typographic template with the shared chrome — no design
work, just readable long-form text.

### 3. Performance — done, with one thing left

A full pass on 2026-09-09. Site imagery went 337 MB (raw handoffs) -> 20 MB
-> **11 MB**, and the homepage stopped pulling its whole image set on first
paint.

Two bugs were behind most of it:

- `optimize.py` never stamped width/height on any image. It builds the file
  path with `os.path.join(SITE, src)` where src is root-absolute
  (`/assets/...`), and join discards everything before an absolute component,
  so every lookup pointed outside the project, Image.open raised, and a bare
  `except` swallowed it. Without intrinsic sizes the browser cannot reserve
  space, so every lazy image sat inside the load threshold at once: the
  homepage fetched 47 images / 1.9 MB before a single scroll. It now fetches
  one. This was also the whole source of the page's layout shift.
- Images were resized to a flat 2048px cap regardless of how large they are
  actually painted. Icons shipped at 1536px to be drawn at 48px; the NBC
  wordmark at 2048px to be drawn at 41px. `_build/display-widths.json` now
  holds the real painted width of all 288 images, measured in a browser at
  1440px and 375px (the larger of the two), and images.py targets 2x that
  with a 200px floor.

**Left to do:** `display-widths.json` is a measurement snapshot, not something
the build derives. Add or restyle a page and its images fall back to the
2048px cap — correct, just heavier than needed. Re-measure when the layout
changes materially.

Also worth knowing: a handful of images are painted larger than the file they
came from, so they are upscaled and soft. The build never upscales, so these
need better source art, not a build change. Worst is
`testosterone/gym-bg.webp` — a 576px file painted at 792px.

### 4. Analytics

The live site runs Google Tag Manager container **GTM-WJWTXMJ4**. None of the
seven rebuilt pages carry any tag. If the same container should follow the
rebuild, add it to `SHELL` in `_build/build.py` so every page gets it.

### 5. Concierge — one thing left open

The page's "Longevity briefing" newsletter modal is `<form id="lbForm">` with
no action and no handler: it collects an email and drops it. Either wire it to
the mailing list or remove the modal. Same class of problem as the homepage
health-assessment quiz, which also submits nowhere.

### 6. Two smaller things

- **Genetics sells two SKUs** — Lifestyle ($499) and Peptide ($399) — and both
  buttons now go to the same link, losing which product the visitor chose. The
  live site uses `?productid=` for this (see `/peptides/`, `/microdosing/`).
  Needs the two SKU ids.
- **11 images were never supplied** — 9 on Men's Optimal Health, 2 on GLP-1.
  They render as red dashed "image needed" boxes. `~/Desktop/Claude/Apex Source
  Content/` has real Apex photography that may cover some of them.

## Live WordPress copy, for reference

Word counts read 2026-09-09, for sizing the remaining work:

    /terms-and-conditions  13,152   /privacy-policy   6,842
    /hormone-therapy        5,276   /about-us         1,586
    /contact-us             1,376   /peptides         1,116
    /supplements              968   /advanced-diag      963
    /partner                  946   /microdosing        820
    /concierge                657   /bloodwork            6  (stub)

`/bloodwork` is effectively empty on the live site — worth asking whether that
page is real before building it.

## Not done, deliberately

Nothing here is blocked on a bug. The build is in good shape; what remains is
content and two decisions (the genetics SKU ids, and whether GTM-WJWTXMJ4
carries over). See `CUTOVER.md` before pointing the domain anywhere.
