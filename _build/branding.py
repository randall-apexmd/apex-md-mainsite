# -*- coding: utf-8 -*-
"""Generate the favicons and social preview images.

Three of the handoff READMEs list "analytics, favicon, OG tags" as not
included, so none of this exists in the source material. It is generated here
rather than hand-made so it stays in step if the logo is ever replaced.

    python3 _build/branding.py

Favicon: the red mark is isolated from `logo-dark.png` by finding the bounding
box of its red pixels, squared up with padding, and written at the sizes a
browser and an iOS home screen actually ask for. The wordmark is dropped — at
32px it is an unreadable smear, and the mark alone is what people recognise
in a tab strip.

OG image: each page's own hero, centre-cropped to the 1.91:1 that Facebook,
LinkedIn, X and iMessage all expect. A page whose hero is already a composed
graphic (Apex AI) previews as that graphic; the rest preview as their
photography.
"""
import os
import sys

from PIL import Image

BUILD = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BUILD)
SRC = os.path.join(ROOT, '_src')
SITE = os.path.join(ROOT, 'site')

LOGO = os.path.join(SRC, 'homepage', 'assets', 'logo-dark.png')

ICO_SIZES = [16, 32, 48, 64, 128, 256]
APPLE = 180
OG_W, OG_H = 1200, 630

# the hero each page should preview as, relative to its handoff's assets/
# Deliberately not the before/after shots: a transformation photo is a poor
# link preview (it reads as an ad, and it carries a results-vary disclaimer
# that a preview card strips away).
OG_SOURCE = {
    'index':                 ('homepage',      'woman-hero.png'),
    'testosterone':          ('testosterone',  'hero.jpg'),
    'genetics':              ('genetics',      'hero-composite-v3.png'),
    'mens-optimal-health':   ('mens-health',   'hero-man.png'),
    'womens-optimal-health': ('womens-health', 'hero-woman-cutout.png'),
    'glp-1-program':         ('weight-loss',   'benefits-collage.png'),
    'apex-md-ai':            ('apex-ai',       'hero.jpg'),
}


def red_mark(logo_path):
    """Crop the red mark out of the horizontal lockup."""
    im = Image.open(logo_path).convert('RGBA')
    px = im.load()
    w, h = im.size

    x0, y0, x1, y1 = w, h, 0, 0
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a > 128 and r > 120 and r > g * 2 and r > b * 2:
                x0, y0 = min(x0, x), min(y0, y)
                x1, y1 = max(x1, x), max(y1, y)

    if x0 > x1 or y0 > y1:
        raise SystemExit('no red pixels found in %s' % logo_path)

    mark = im.crop((x0, y0, x1 + 1, y1 + 1))

    # square it, then pad — a favicon that touches its own edges looks cramped
    side = max(mark.size)
    pad = int(side * 0.14)
    canvas = Image.new('RGBA', (side + pad * 2, side + pad * 2), (0, 0, 0, 0))
    canvas.paste(mark,
                 ((canvas.width - mark.width) // 2,
                  (canvas.height - mark.height) // 2),
                 mark)
    return canvas


def favicons():
    mark = red_mark(LOGO)

    ico = os.path.join(SITE, 'favicon.ico')
    mark.save(ico, sizes=[(s, s) for s in ICO_SIZES])

    for size, name in ((APPLE, 'apple-touch-icon.png'),
                       (192, 'icon-192.png'),
                       (512, 'icon-512.png')):
        img = mark.resize((size, size), Image.LANCZOS)
        if name == 'apple-touch-icon.png':
            # iOS squares the corners itself and does not honour alpha, so
            # give it a white ground instead of the black it would default to
            flat = Image.new('RGB', (size, size), '#ffffff')
            flat.paste(img, (0, 0), img)
            img = flat
        img.save(os.path.join(SITE, name))

    print('  favicon.ico  %s' % ' '.join('%dx%d' % (s, s) for s in ICO_SIZES))
    print('  apple-touch-icon.png, icon-192.png, icon-512.png')


def og_images():
    out_dir = os.path.join(SITE, 'assets', 'og')
    os.makedirs(out_dir, exist_ok=True)

    for slug, (handoff, name) in sorted(OG_SOURCE.items()):
        src = os.path.join(SRC, handoff, 'assets', name)
        if not os.path.isfile(src):
            print('  %-22s SKIP — %s not found' % (slug, name))
            continue

        with Image.open(src) as im:
            im = im.convert('RGB') if im.mode != 'RGBA' else im
            if im.mode == 'RGBA':
                flat = Image.new('RGB', im.size, '#ffffff')
                flat.paste(im, (0, 0), im)
                im = flat

            # cover-fit to 1200x630, cropping the overflow from the centre
            scale = max(OG_W / im.width, OG_H / im.height)
            im = im.resize((max(1, round(im.width * scale)),
                            max(1, round(im.height * scale))), Image.LANCZOS)
            left = (im.width - OG_W) // 2
            top = (im.height - OG_H) // 2
            im = im.crop((left, top, left + OG_W, top + OG_H))
            im.save(os.path.join(out_dir, slug + '.jpg'),
                    'JPEG', quality=84, optimize=True, progressive=True)

        kb = os.path.getsize(os.path.join(out_dir, slug + '.jpg')) // 1024
        print('  %-22s %dx%d  %dK' % (slug, OG_W, OG_H, kb))


if __name__ == '__main__':
    print('favicons')
    favicons()
    print('og images')
    og_images()
