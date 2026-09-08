# -*- coding: utf-8 -*-
"""Resize and re-encode the handoff imagery for the web.

The handoffs ship print-scale source art: 337 MB across the seven pages, with
single files up to 11 MB and one page (Women's Optimal Health) at 107 MB. No
amount of lazy-loading rescues that — the bytes have to come down.

Two passes per file:

  resize   nothing needs to exceed MAX_EDGE. These are 2x assets for a 1440px
           comp, so 2048px on the long edge is already generous; a 4000px
           source is scanner output, not a design decision.
  re-encode WebP at q82, which is the format's sweet spot and carries alpha,
           so transparent product cutouts survive the conversion that a
           JPEG would flatten onto black.

Filenames change extension, so build.py rewrites the page's references to
match. Re-runs are cheap: an output newer than its source is left alone.
"""
import os

from PIL import Image

MAX_EDGE = 2048
QUALITY = 82

# Anything already small and hand-tuned is left exactly as it is.
SKIP_EXT = {'.svg', '.ico', '.webp'}


def _has_alpha(im):
    if im.mode in ('RGBA', 'LA'):
        # a fully-opaque alpha channel is just wasted bytes
        alpha = im.getchannel('A')
        return alpha.getextrema()[0] < 255
    return im.mode == 'P' and 'transparency' in im.info


def optimise(src, dst_dir, name):
    """Write an optimised copy into dst_dir. Returns (filename, before, after)."""
    stem, ext = os.path.splitext(name)
    ext = ext.lower()
    before = os.path.getsize(src)

    if ext in SKIP_EXT:
        dst = os.path.join(dst_dir, name)
        if not os.path.exists(dst) or os.path.getmtime(dst) < os.path.getmtime(src):
            with open(src, 'rb') as a, open(dst, 'wb') as b:
                b.write(a.read())
        return name, before, before

    out_name = stem + '.webp'
    dst = os.path.join(dst_dir, out_name)

    if os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(src):
        return out_name, before, os.path.getsize(dst)

    with Image.open(src) as im:
        im.load()
        keep_alpha = _has_alpha(im)
        im = im.convert('RGBA' if keep_alpha else 'RGB')

        w, h = im.size
        if max(w, h) > MAX_EDGE:
            scale = MAX_EDGE / float(max(w, h))
            im = im.resize((max(1, round(w * scale)), max(1, round(h * scale))),
                           Image.LANCZOS)

        im.save(dst, 'WEBP', quality=QUALITY, method=6)

    return out_name, before, os.path.getsize(dst)


def human(n):
    for unit in ('B', 'K', 'M'):
        if abs(n) < 1024 or unit == 'M':
            return '%.0f%s' % (n, unit) if unit != 'M' else '%.1fM' % n
        n /= 1024.0
