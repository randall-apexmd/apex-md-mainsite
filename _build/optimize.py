# -*- coding: utf-8 -*-
"""Stamp loading hints and intrinsic dimensions onto every <img>.

Ported from the eos site with one deliberate difference. That site's design
shipped two complete renderings and hid one with `display:none`; browsers
still download images inside a hidden subtree, so EVERY image there had to be
lazy for the hidden rendering to cost nothing.

These handoffs ship a single rendering, so blanket lazy-loading only hurts —
it defers the hero, which is the LCP element on all seven pages. So the first
image loads eagerly at high priority and everything after it is lazy. (A
straight port marked the hero both `loading=lazy` and `fetchpriority=high`,
which tells the browser to defer it and to rush it at the same time.)

Intrinsic width/height come from the real files so the browser can reserve
space and avoid layout shift as images arrive.

Run via build.py; safe to re-run (attributes are replaced, not duplicated).
"""
import os, re
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, 'site')

_dims = {}
def dims(src):
    """Intrinsic size of an image, by its src as written in the HTML.

    The src is root-absolute (`/assets/images/...`). os.path.join discards
    everything before an absolute component, so join(SITE, src) silently
    returned a path outside the project, Image.open raised, the bare except
    swallowed it, and every image shipped without width/height.

    That is not a cosmetic loss. With no intrinsic size the browser cannot
    reserve space: the page collapses at parse time, every lazy image lands
    inside the load threshold at once, and the homepage pulled its whole
    1.9 MB of imagery on first paint instead of the ~200 KB above the fold.
    It is also the entire source of the page's layout shift.
    """
    if src not in _dims:
        rel = src.split('?')[0].split('#')[0].lstrip('/')
        path = os.path.join(SITE, rel)
        try:
            with Image.open(path) as im:
                _dims[src] = im.size
        except (OSError, ValueError) as exc:
            print('      no dimensions for %s (%s)' % (rel, exc.__class__.__name__))
            _dims[src] = None
    return _dims[src]


def optimize(path):
    s = open(path, encoding='utf-8').read()

    first = True
    out, changed = [], 0

    for m in re.finditer(r'<img\b[^>]*>', s):
        tag = m.group(0)
        src_m = re.search(r'src="([^"]+)"', tag)
        if not src_m:
            continue
        src = src_m.group(1)

        # strip any attributes we are about to set, so re-running is idempotent
        new = re.sub(r'\s+(loading|decoding|fetchpriority|width|height)="[^"]*"', '', tag)

        # the hero is the LCP candidate: fetch it eagerly and early
        if first:
            first = False
            attrs = ' loading="eager" decoding="async" fetchpriority="high"'
        else:
            attrs = ' loading="lazy" decoding="async"'

        # NB: test for the ATTRIBUTE, not the substring — every tag carries a
        # style="" that mentions width/height, which matched a naive check.
        wh = dims(src)
        has_attr = re.search(r'\s(width|height)=', new)
        if wh and not has_attr:
            attrs += f' width="{wh[0]}" height="{wh[1]}"'

        new = new[:-1].rstrip() + attrs + '>'
        out.append((m.start(), m.end(), new))
        changed += 1

    for start, end, new in reversed(out):
        s = s[:start] + new + s[end:]

    open(path, 'w', encoding='utf-8').write(s)
    return changed


if __name__ == '__main__':
    import glob
    for f in sorted(glob.glob(os.path.join(SITE, '*.html'))):
        n = optimize(f)
        print(f'  {os.path.basename(f):22s} {n} <img> optimised')
