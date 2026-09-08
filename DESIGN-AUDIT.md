# Apex MD main site — design audit of the seven handoffs

Read before building. Source: the Drive download in
`~/Desktop/Claude/Apex MD Main Site`, copied to `_src/` (gitignored).

## The problem in one table

| Page | Heading font | Accent | Container | Mobile |
|---|---|---|---|---|
| Homepage | Poppins | `#E02424` | 1440px | 1 breakpoint @860px |
| GLP-1 Weight Loss | Plus Jakarta Sans | `#e8232a` | — | none |
| Testosterone | Archivo | `#d30704` | 1240px | none, `min-width:1200px` |
| Genetics | Archivo | `#d30704` | 1560/1240px | none, `min-width:1200px` |
| Men's Optimal Health | Archivo | `#d30704` | — | none |
| Women's Optimal Health | Archivo | `#c2185b` | — | none |
| Apex MD AI | Archivo | `#e11d2a` | — | 6 breakpoints |

Three font stacks. Five reds — four of them near-identical, which is worse than
five different ones, because the mismatch reads as a rendering bug rather than
a choice. Four pages have **no mobile layout at all**, and two of those actively
fight one with a `min-width: 1200px` page wrapper.

## What each handoff says about itself

Every README states the same thing in different words: *this is a design
reference, not shippable code.* Specifically:

- **Homepage** — "not meant to be shipped verbatim… recreate this design in
  your target codebase." Ships a 9-step Free Health Assessment quiz with real
  recommendation logic, but it **submits nowhere**.
- **Testosterone** — "Built desktop-first; the page wrapper sets
  `min-width:1200px`. Mobile breakpoints still need to be written. The grids
  are the work."
- **Genetics** — same wrapper problem, plus "a handful of card images are still
  dashed `div.img-placeholder` blocks."
- **Women's / Men's** — reflow to ~380px without media queries, but "no
  mobile-specific navigation is included."
- **Weight Loss** — needs `support.js` + `image-slot.js` at runtime; the
  standalone file is 9.2 MB of base64.
- **Apex MD AI** — the rendered export is 24 MB of base64.

## Shared chrome does not exist yet

No two pages agree on a header. Men's and Women's link a real nav to
`https://apexmd.com/...`; Homepage, Testosterone, Genetics and Apex AI use
`href="#"` placeholders. The Homepage README specifies the canonical structure —
About Us / Concierge Care / Programs ▾ / Products ▾ / Apex MD AI / Partner /
Contact + a red Patient Login pill, with a footer that mirrors it — so that is
the natural source for `_build/parts/`.

## CTA destinations conflict

| Page | Sends users to |
|---|---|
| Men's, Women's | `labs.rupahealth.com` storefront (15 and 24 links) |
| GLP-1 Weight Loss | `formmac.apexmd.com?categoryId=weight-loss` |
| Homepage | the assessment quiz, which submits nowhere |
| Testosterone, Genetics, Apex AI | `href="#"` |

The eos site settled this pattern with `formeos.apexmd.com?categoryId=…`.
The main site needs the same decision made once, in one place.

## Assets

560 MB across 406 PNGs and 79 JPEGs, unoptimised — single images run to 11 MB
(`homepage/assets/card-mens-t-v2.png`). These need a resize/compress pass into
`site/assets/images/` before anything is deployed. `_build/optimize.py` handles
the `<img>` attributes; the bitmaps themselves need the pass first.

Three handoffs also flag their imagery as AI-generated composites or unlicensed
stock, to be replaced with real photography before launch.

## Copy needing sign-off before it goes public

Called out by the handoffs themselves, not by me:

- Women's: the estrogen/Alzheimer's section and hormone-therapy descriptions
  were "written from general medical knowledge"; testimonial names and the
  case-study figures are placeholders; patient photos need signed releases.
- Testosterone: "300,000+ patients", "4.8/5", and specific lbs / ng/dL figures
  need compliance review; before/afters need a results-vary disclaimer.
- Genetics: the "not a diagnostic test" FAQ language needs a compliance read.
- Pricing appears in several places per page and must be reconciled:
  $129 + $199/mo (TRT) · $199 / $399 (Women's) · $149 / $399 (Homepage quiz) ·
  $499 / $399 (Genetics).

## Recommendation

Adopt the **Archivo + `#d30704`** system as the house style. It already carries
four of the seven pages (Testosterone, Genetics, Men's, Women's), so it is the
smallest total change: re-theme Homepage, Weight Loss and Apex AI to match,
rather than re-theming four pages to the Homepage's Poppins.

Women's `#c2185b` pink is the one deliberate divergence — it reads as a section
accent for the women's line, not a mistake. Worth keeping as a scoped accent
if that was the intent.

Then: extract chrome from the Homepage spec into `parts/`, pin the tokens in
`style.py`, and write the mobile layer once, centrally — it does not exist on
four of the seven pages and is the single largest piece of work in this build.
