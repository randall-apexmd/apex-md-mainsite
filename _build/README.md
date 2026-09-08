# _build — page assembler for apexmd.com

The site is plain static HTML. Vercel serves `site/` as-is; there is no build
step in the deploy. This folder is a local tool Claude runs to keep the pages
consistent — Blake never needs to run it.

    python3 _build/build.py      # regenerates every page in site/

## Why it exists

The seven pages arrived as seven *independent* Claude Design handoffs, authored
weeks apart by different passes. They do not share a header, a footer, a font
stack, or an accent red (see `../DESIGN-AUDIT.md`). Shipping them verbatim
gives visitors seven different websites under one domain.

So the chrome is extracted once into `parts/`, the token vocabulary is pinned
in `style.py`, and every page is stamped from those.

## Layout

    style.py      the pinned token vocabulary (colours, type, spacing)
    cssx.py       hoists inline styles into classes, generates the mobile layer
    build.py      page assembly: chrome, relinking, asset pipeline
    images.py     resize + WebP re-encode (337 MB -> 20 MB)
    optimize.py   stamps width/height and loading hints onto every <img>
    branding.py   favicons and social preview images
    parts/        the shared chrome — the only place to edit header/footer

## Source material

`../_src/` holds the seven design handoffs from the Drive download. It is
gitignored (~560 MB of unoptimised PNGs); the canonical copy is in Drive.

    _src/homepage        Poppins    #E02424   1 breakpoint
    _src/weight-loss     Jakarta    #e8232a   none
    _src/testosterone    Archivo    #d30704   none
    _src/genetics        Archivo    #d30704   none
    _src/mens-health     Archivo    #d30704   none
    _src/womens-health   Archivo    #c2185b   none
    _src/apex-ai         Archivo    #e11d2a   6 breakpoints

## Rules

- Chrome in `parts/` is copied verbatim. Don't hand-edit generated pages; edit
  the renderer or the content module and rebuild.
- Section markup follows `style.py`. Don't introduce colours or spacing that
  aren't already in the pinned vocabulary — that is how the handoffs drifted
  apart in the first place.
- Copy comes from the handoff, which was written for a design comp and is
  flagged in several places as needing medical/compliance sign-off. Nothing
  ships to production copy without Blake's say-so.
- Every page must carry the same header and footer, or the site reads as seven
  microsites.
