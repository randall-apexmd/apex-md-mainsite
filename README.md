# apexmd.com

Static site for Apex MD. Vercel serves `site/` as-is — no build step in the
deploy, no framework, no npm.

`vercel.json` lives at the repo root (not in `site/`) and sets
`outputDirectory: "site"`. Vercel only reads a root-level `vercel.json`, so
keeping it here means the project needs no dashboard configuration — leave
Root Directory empty and everything resolves.

    python3 _build/build.py          # rebuild every page into site/
    python3 _build/build.py genetics # or just one
    python3 _build/branding.py       # favicons + social preview images

## Layout

    site/        what gets deployed. Generated — do not hand-edit.
    _build/      the assembler that produces it (see _build/README.md)
    _src/        the seven design handoffs. Gitignored, ~560 MB.
    DESIGN-AUDIT.md   why the handoffs needed reconciling
    CUTOVER.md        how to point apexmd.com here without breaking email

## Where the source material lives

`_src/` is a working copy of the Drive download that currently sits in
`~/Desktop/Claude/Apex MD Main Site`. It is not committed — 560 MB of
print-scale PNGs. To rebuild from scratch on another machine, re-download that
folder and unzip each page's export into `_src/<slug>/`; `_build/build.py`
lists the expected paths in `PAGES`.

## What the build does

Seven pages were designed independently and shared nothing — three font
stacks, five reds, and no mobile layout on four of them. The build reconciles
them:

- swaps every page onto Archivo + `#d30704` (`_build/style.py`)
- replaces each page's own header and footer with the shared chrome in
  `_build/parts/`, which is the only place they should ever be edited
- hoists ~4,900 inline `style` attributes into generated stylesheets, which is
  what makes a mobile layer possible at all — a media query cannot override an
  inline style (`_build/cssx.py`)
- generates that mobile layer: collapses grids, unblocks the `min-width:1200px`
  desktop-only wrappers, wraps flex rows, scales oversized type and padding
- points every CTA at the real intake form, using the category vocabulary
  read off the live site (`weight-loss`, `trt`, `bloodwork`, `hrt`)
- resizes and re-encodes the imagery to WebP — 337 MB down to 20 MB

## Status

All seven pages build and render at desktop and mobile. Before this can be the
live apexmd.com, read `CUTOVER.md` — in short: 58 live WordPress URLs have no
destination here yet, two CTA categories are guesses worth checking, and the
copy has not cleared compliance.
