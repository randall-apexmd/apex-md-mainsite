# -*- coding: utf-8 -*-
"""Assemble site/ from the seven design handoffs in _src/.

    python3 _build/build.py            # every page
    python3 _build/build.py testosterone genetics

For each page: strip the handoff's own header/footer, stamp the shared chrome
from parts/, hoist the inline styles into a generated stylesheet (cssx), fold
the outlier accents onto the house red, copy the referenced assets, and write
site/<slug>.html.

Generated pages are disposable. Edit parts/, style.py, or the handoff — never
a file in site/.
"""
import base64
import datetime
import hashlib
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cssx
import images
import style as S

BUILD = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BUILD)
SRC = os.path.join(ROOT, '_src')
SITE = os.path.join(ROOT, 'site')
PARTS = os.path.join(BUILD, 'parts')

# slug -> (handoff dir, entry file, nav section it belongs to)
PAGES = {
    'index':                 ('homepage',      'index.html',                 None),
    'testosterone':          ('testosterone',  'index.html',                 'programs'),
    'genetics':              ('genetics',      'index.html',                 'products'),
    'mens-optimal-health':   ('mens-health',   'index.html',                 'programs'),
    'womens-optimal-health': ('womens-health', 'index.html',                 'programs'),
    'glp-1-program':         ('weight-loss',   'index.dc.html',              'programs'),
    'apex-md-ai':            ('apex-ai',       'Apex MD AI Landing.dc.html', 'apex-md-ai'),
    'concierge':             ('concierge',     'index.html',                 'concierge'),
}


# Where each page's CTAs send people.
#
# Read off the live WordPress site on 2026-09-09 by crawling all 68 sitemap
# URLs — these are the intake categories that actually exist, not invented
# ones. Verified live: form.apexmd.com/, ?categoryId=trt and
# ehr.apexmd.com/login all return 200.
#
# The category vocabulary in use is exactly: weight-loss, trt, bloodwork,
# hrt, microdosing (plus per-product ?productid= links, and a partner
# subdomain form10fitness.apexmd.com). There is no genetics category.
#
# CONFIRMED — the live page for this product uses this exact URL:
#   testosterone    ?categoryId=trt        (live /testosterone-apexmd/)
#   glp-1-program   ?categoryId=weight-loss (live /glp-1-program/)
#
# INFERRED — flagged in CUTOVER.md, change here if wrong. Men's and Women's
# Optimal Health are structurally the same page and both sell the $199
# "Optimization Jumpstart" (labs + clinician read), so they point at
# bloodwork. Women's could arguably be hrt instead.
#
# Genetics has no category of its own on the live form. Blake directed it to
# bloodwork, which is the closest fit — it is a lab-ordered test either way.
# Note this flattens two distinct SKUs onto one link: the page sells Lifestyle
# Genetics ($499) and Peptide Genetics ($399) as separate buttons, and both
# now land on the same uncategorised-by-product intake. If those SKUs have
# ?productid= values, put them here and split the two buttons.
#
# UNMAPPED — sent to the generic form with no category preselected rather
# than guessed into the wrong one. Better a visitor picks their own category
# than lands in someone else's.
FORM = 'https://form.apexmd.com/'
LOGIN = 'https://ehr.apexmd.com/login'

CTA = {
    'index':                 FORM,
    'apex-md-ai':            FORM,
    'genetics':              FORM + '?categoryId=bloodwork',
    'concierge':             FORM + '?categoryId=bloodwork',
    'testosterone':          FORM + '?categoryId=trt',
    'glp-1-program':         FORM + '?categoryId=weight-loss',
    'mens-optimal-health':   FORM + '?categoryId=bloodwork',
    'womens-optimal-health': FORM + '?categoryId=bloodwork',
}


# Title and description for the pages whose handoff shipped none (the three
# .dc.html canvas exports carry no <title>, and two others no description).
# Every string below is lifted from that page's own hero copy — nothing here
# is a new marketing claim.
META = {
    'index': (
        None,
        'Physician-guided wellness solutions and products powered by Apex MD '
        'AI, which analyzes your data, health questions, and delivers '
        'personalized insights so you can live better longer.'),
    'mens-optimal-health': (
        None,
        'Testosterone and metabolic imbalance are measurable. Apex MD tests '
        'yours, a clinician reads the results with you, and you get a '
        'protocol built for your biology.'),
    'glp-1-program': (
        'GLP-1 Weight Loss Program | Apex MD',
        'Prescription GLP-1 with personalized dosing and quarterly '
        'bloodwork, so you burn fat without losing the muscle you have '
        'built. Physician guidance and AI-powered tracking included.'),
    'apex-md-ai': (
        'Apex MD AI — One Platform. Complete Clarity.',
        'Apex MD AI analyzes your data, uncovers what matters, and delivers '
        'personalized insights so you can optimize your health with '
        'confidence.'),
}


# --------------------------------------------------------------- helpers

def read(path):
    with open(path, encoding='utf-8', errors='replace') as fh:
        return fh.read()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(text)


def meta(html, name):
    m = re.search(r'<meta\s+name="%s"\s+content="([^"]*)"' % name, html, re.I)
    return m.group(1) if m else ''


def title(html):
    m = re.search(r'<title>(.*?)</title>', html, re.S | re.I)
    return m.group(1).strip() if m else 'Apex MD'


def body_of(html):
    m = re.search(r'<body[^>]*>(.*)</body>', html, re.S | re.I)
    return m.group(1) if m else html


def page_style(html, page):
    """The handoff's own <style> block: keyframes, .ico classes, resets.

    The reset and link colours are dropped — apex.css owns those, and keeping
    both means whichever loads last wins. Keyframes and page-specific classes
    are kept, normalised onto the house palette.
    """
    out = []
    for m in re.finditer(r'<style[^>]*>(.*?)</style>', html, re.S | re.I):
        css = m.group(1)
        # drop rules apex.css already owns, so they cannot fight
        css = re.sub(r'(^|\})\s*\*\s*\{[^}]*\}', r'\1', css)
        css = re.sub(r'(^|\})\s*body\s*\{[^}]*\}', r'\1', css)
        css = re.sub(r'(^|\})\s*a\s*\{[^}]*\}', r'\1', css)
        css = re.sub(r'(^|\})\s*a:hover\s*\{[^}]*\}', r'\1', css)
        css = re.sub(r'(^|\})\s*h1\s*,\s*h2\s*,\s*h3\s*,\s*h4\s*\{[^}]*\}', r'\1', css)
        css = re.sub(r'(^|\})\s*::selection\s*\{[^}]*\}', r'\1', css)
        out.append(cssx.normalise(css, page).strip())
    return '\n'.join(x for x in out if x)


def strip_chrome(body):
    """Remove the handoff's own header and footer.

    Each page brought its own, and no two agree; the shared parts replace them.

    The sticky product bar that Men's and Women's pin to the viewport bottom is
    deliberately kept: it is page-specific, carries that page's own pricing,
    and is not chrome.
    """
    n = 0
    for tag in ('header', 'footer'):
        body, k = re.subn(r'<%s\b.*?</%s>' % (tag, tag), '', body, flags=re.S | re.I)
        n += k

    # The Weight Loss handoff puts its Google Fonts <link> in the body. The
    # shell already loads the house stack, so this only re-downloads a font
    # (Plus Jakarta Sans) that nothing on the built page uses any more.
    body = re.sub(r'<link[^>]*fonts\.(?:googleapis|gstatic)\.com[^>]*>', '',
                  body, flags=re.I)
    return body, n


def clean_design_tool(body):
    """Strip the authoring tool's runtime scaffolding.

    Three of the handoffs are `.dc.html` canvas files that expect `support.js`
    to render them. We ship static HTML instead, so the scaffolding has to go
    or it leaks:

      <helmet>     holds the <link>/<style> the shell already provides
      <x-dc>       the canvas wrapper; an unknown element defaults to
                   display:inline, so it reports zero height and its
                   whitespace prints as stray inline text
      <sc-if>      a conditional whose test never runs, so it renders its
                   body unconditionally — this is what puts the literal
                   "{{ announceText }}" on the Apex AI page
      <image-slot> a deliberate image placeholder the designer left unfilled

    image-slot becomes a visible dashed box captioned with its intended
    subject, so an unfinished image reads as unfinished instead of as an
    empty gap nobody notices.
    """
    counts = {'helmet': 0, 'x-dc': 0, 'sc-if': 0, 'image-slot': 0}

    body, n = re.subn(r'<helmet\b.*?</helmet>', '', body, flags=re.S | re.I)
    counts['helmet'] = n

    body, n = re.subn(r'</?x-dc\b[^>]*>', '', body, flags=re.I)
    counts['x-dc'] = n

    # only the conditionals that never resolved; a filled one has no {{ }}
    def drop_if(m):
        return '' if '{{' in m.group(0) else m.group(0)

    body, n = re.subn(r'<sc-if\b.*?</sc-if>', drop_if, body, flags=re.S | re.I)
    counts['sc-if'] = n

    def slot(m):
        attrs = m.group(1)
        cls = re.search(r'class="([^"]*)"', attrs)
        label = re.search(r'placeholder="([^"]*)"', attrs)
        counts['image-slot'] += 1
        return ('<div class="%s img-todo" data-todo="%s">'
                % (cls.group(1) if cls else '',
                   label.group(1) if label else 'image'))

    body = re.sub(r'<image-slot\b([^>]*)>', slot, body, flags=re.I)
    body = re.sub(r'</image-slot>', '</div>', body, flags=re.I)

    # any template expression still standing would print as literal text
    body = re.sub(r'\{\{[^{}]*\}\}', '', body)

    return body, counts


def chrome(part, active, slug):
    html = read(os.path.join(PARTS, part))
    html = html.replace('/get-started', CTA.get(slug, FORM))
    html = html.replace('/patient-login', LOGIN)
    # the note at the top of each part is for whoever edits it, not for the
    # wire — and it contains a {{ }} token that the template sweep would eat
    html = re.sub(r'<!--.*?-->', '', html, flags=re.S).lstrip()
    html = html.replace('{{YEAR}}', str(datetime.date.today().year))
    if active:
        html = html.replace('data-nav="%s"' % active,
                            'data-nav="%s" class="is-active"' % active)
    return html


def relink(body, slug):
    """Point navigation at apexmd.com routes and CTAs at the real intake form.

    The handoffs disagree wildly: Men's and Women's send 39 links to a Rupa
    Health storefront, Weight Loss to the partner subdomain
    formmac.apexmd.com, and Homepage, Testosterone, Genetics and Apex AI use
    bare `href="#"` placeholders that go nowhere.

    All of it resolves to two places: in-site navigation becomes a relative
    apexmd.com path (so a staging deploy does not bounce visitors to
    production), and anything that was a call to action becomes this page's
    entry in CTA above.
    """
    cta = CTA.get(slug, FORM)
    counts = {'absolute': 0, 'rupa': 0, 'placeholder': 0}

    body, n = re.subn(r'href="https://apexmd\.com/?', 'href="/', body)
    counts['absolute'] = n

    # Catch these anywhere, not just in an href. The Women's handoff ships a
    # component whose script carries `ctaHref: ... ?? 'https://labs.rupa...'`
    # as a runtime default, so an href-only rewrite leaves a live off-site CTA
    # that only fires once the component renders.
    body, n = re.subn(
        r'https://(?:labs\.rupahealth\.com|form[a-z0-9-]*\.apexmd\.com)[^"\'\s<>]*',
        cta, body)
    counts['rupa'] = n

    # bare placeholders, but not real in-page anchors like href="#faq"
    body, n = re.subn(r'href="#"', 'href="%s"' % cta, body)
    counts['placeholder'] = n

    # the two routes that live outside this site
    body = body.replace('href="/get-started"', 'href="%s"' % cta)
    body = body.replace('href="/patient-login"', 'href="%s"' % LOGIN)

    return body, counts


def extract_data_uris(body, handoff):
    """Pull base64-inlined images out into real files.

    The Concierge handoff embeds all of its images as `data:` URIs, which is
    why that file is 2.8 MB. An inline image cannot be cached, cannot be
    lazy-loaded, cannot be resized by the image pipeline, and costs a third
    more bytes than the binary it encodes. Written out as files they go
    through the same resize/WebP pass as everything else.

    Named by content hash, so a repeated image is stored once and re-running
    the build is stable.
    """
    out_dir = os.path.join(SRC, handoff, 'assets')
    pat = re.compile(r'data:image/([a-zA-Z0-9.+-]+);base64,([A-Za-z0-9+/=\s]+)')
    seen, count = {}, [0]

    def repl(m):
        fmt, data = m.group(1).lower(), re.sub(r'\s+', '', m.group(2))
        try:
            raw = base64.b64decode(data, validate=True)
        except Exception:                                    # noqa: BLE001
            return m.group(0)
        digest = hashlib.sha1(raw).hexdigest()[:12]
        if digest not in seen:
            ext = {'jpeg': 'jpg', 'svg+xml': 'svg'}.get(fmt, fmt)
            name = 'inline-%s.%s' % (digest, ext)
            os.makedirs(out_dir, exist_ok=True)
            path = os.path.join(out_dir, name)
            if not os.path.exists(path):
                with open(path, 'wb') as fh:
                    fh.write(raw)
            seen[digest] = name
            count[0] += 1
        return 'assets/' + seen[digest]

    return pat.sub(repl, body), count[0]


def rewrite_assets(body, slug):
    """Repoint the handoff's relative asset paths at the built site.

    Every handoff loads images as `assets/<file>`, relative to its own folder.
    Built pages sit at the site root, so those become
    `/assets/images/<slug>/<file>` — namespaced per page because the seven
    handoffs reuse filenames (`hero.jpg` appears in four of them) with
    different images behind them.
    """
    def sub(pattern, repl):
        return re.subn(pattern, repl, body)

    n = 0
    for folder in ('assets', 'uploads'):
        body, k = re.subn(
            r'(src|href)="%s/' % folder,
            r'\1="/assets/images/%s/' % slug, body)
        n += k
        body, k = re.subn(
            r'url\((["\']?)%s/' % folder,
            r'url(\1/assets/images/%s/' % slug, body)
        n += k
    return body, n


def copy_assets(handoff, slug, referenced):
    """Optimise the assets the page references, and only those.

    The handoff folders carry duplicates and working files — Genetics alone
    ships 61 MB for a page that uses a fraction of it. Each referenced file is
    resized and re-encoded to WebP on the way in (see images.py), so the
    filename changes; the caller rewrites the page's references from the
    returned map.
    """
    dst_dir = os.path.join(SITE, 'assets', 'images', slug)
    mapping, missing = {}, []
    before = after = 0

    for name in sorted(referenced):
        src = None
        for folder in ('assets', 'uploads'):
            cand = os.path.join(SRC, handoff, folder, name)
            if os.path.isfile(cand):
                src = cand
                break
        if not src:
            missing.append(name)
            continue

        os.makedirs(dst_dir, exist_ok=True)
        try:
            out, b, a = images.optimise(src, dst_dir, name)
        except Exception as exc:                      # noqa: BLE001
            print('    could not optimise %s (%s) — copying as-is' % (name, exc))
            shutil.copy2(src, os.path.join(dst_dir, name))
            out = name
            b = a = os.path.getsize(src)
        mapping[name] = out
        before += b
        after += a

    return mapping, missing, before, after


def referenced_assets(body, slug):
    """Filenames the built page asks for under /assets/images/<slug>/.

    Two things the naive pattern gets wrong: the Weight Loss handoff appends
    cache-busting query strings (`feat-muscle.png?v=3`), and the Apex AI
    handoff has filenames containing spaces (`Apex MD AI Brain.png`). So match
    to the closing delimiter, then strip the query.
    """
    pat = r'/assets/images/%s/([^"\')]+)' % re.escape(slug)
    out = set()
    for hit in re.findall(pat, body):
        out.add(hit.split('?')[0].split('#')[0].strip())
    return {x for x in out if x}


# ------------------------------------------------------------ page build

SHELL = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="https://apexmd.com{url_path}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Apex MD">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="https://apexmd.com{url_path}">
<meta property="og:image" content="https://apexmd.com/assets/og/{slug}.jpg">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{desc}">
<meta name="twitter:image" content="https://apexmd.com/assets/og/{slug}.jpg">
<meta name="theme-color" content="#d30704">
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="{fonts}" rel="stylesheet">
<link rel="stylesheet" href="/assets/css/apex.css">
<link rel="stylesheet" href="/assets/css/{slug}.css">
{page_css}</head>
<body>
{header}
<main id="main">
{body}
</main>
{footer}
<script src="/assets/js/apex.js" defer></script>
</body>
</html>
"""


def build(slug):
    handoff, entry, active = PAGES[slug]
    path = os.path.join(SRC, handoff, entry)
    if not os.path.exists(path):
        print('  %-22s SKIP — %s not found' % (slug, entry))
        return None

    raw = read(path)
    body = body_of(raw)
    body, dropped = strip_chrome(body)

    # Normalise the whole body, not just the style attributes. The handoffs
    # carry their accent in three more places cssx never sees: inline SVG
    # `fill=`/`stroke=` presentation attributes, `var(--accent,#e8232a)`
    # fallbacks, and the design tool's escaped JSON metadata blocks. Miss
    # these and every icon on the Homepage and Weight Loss pages keeps its
    # old red while the text around it turns house red.
    body = cssx.normalise(body, slug)
    body, tool = clean_design_tool(body)

    body, links = relink(body, slug)
    body, inlined = extract_data_uris(body, handoff)
    body, repathed = rewrite_assets(body, slug)

    # the Apex AI handoff wraps its content in its own <main>; the shell
    # already provides one, and nesting them is invalid HTML that confuses
    # screen-reader landmark navigation.
    body = re.sub(r'<main\b([^>]*)>', r'<div\1>', body, flags=re.I)
    body = re.sub(r'</main>', '</div>', body, flags=re.I)

    ex = cssx.Extractor(slug)
    body, hoisted = cssx.rewrite(body, ex)
    write(os.path.join(SITE, 'assets', 'css', slug + '.css'), ex.stylesheet())

    pcss = page_style(raw, slug)
    pcss = '<style>\n%s\n</style>\n' % pcss if pcss else ''

    over_title, over_desc = META.get(slug, (None, None))
    page_title = over_title or title(raw)
    page_desc = over_desc or meta(raw, 'description')

    html = SHELL.format(
        title=page_title,
        desc=page_desc.replace('"', '&quot;'),
        url_path='/' if slug == 'index' else '/' + slug,
        fonts=S.GOOGLE_FONTS + S.EXTRA_FONTS.get(slug, ''),
        slug=slug,
        page_css=pcss,
        header=chrome('header.html', active, slug),
        footer=chrome('footer.html', None, slug),
        body=body.strip(),
    )
    mapping, missing, before, after = copy_assets(
        handoff, slug, referenced_assets(html, slug))

    # the optimiser changes extensions, so repoint the page at what it wrote
    for old, new_name in mapping.items():
        if old != new_name:
            html = html.replace('/assets/images/%s/%s' % (slug, old),
                                '/assets/images/%s/%s' % (slug, new_name))

    write(os.path.join(SITE, slug + '.html'), html)

    st = ex.stats()
    saved = (1 - after / before) * 100 if before else 0
    print('  %-22s %4d styles -> %3d classes | %2d chrome dropped | '
          '%3d links | %3d img %s -> %s (-%.0f%%) | mobile %d'
          % (slug, hoisted, st['classes'], dropped, sum(links.values()),
             len(mapping), images.human(before), images.human(after),
             saved, st['mobile']))
    if inlined:
        print('    %d base64 image(s) extracted to files' % inlined)
    if tool['image-slot']:
        print('    %d unfilled image placeholder(s) — shown as dashed boxes'
              % tool['image-slot'])
    if missing:
        print('    %d referenced asset(s) not in the handoff: %s'
              % (len(missing), ', '.join(sorted(missing)[:6])))
    return st


def sitemap():
    """Write sitemap.xml for the pages that exist.

    robots.txt already advertises it. Only built pages are listed — a sitemap
    that names a URL which 404s is worse than no sitemap, because Search
    Console reports it as an error against the whole domain.
    """
    today = datetime.date.today().isoformat()
    urls = []
    for slug in sorted(PAGES):
        if not os.path.isfile(os.path.join(SITE, slug + '.html')):
            continue
        loc = 'https://apexmd.com' + ('/' if slug == 'index' else '/' + slug)
        urls.append('  <url>\n    <loc>%s</loc>\n'
                    '    <lastmod>%s</lastmod>\n  </url>' % (loc, today))

    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           + '\n'.join(urls) + '\n</urlset>\n')
    write(os.path.join(SITE, 'sitemap.xml'), xml)
    return len(urls)


def main(argv):
    slugs = argv or list(PAGES)
    bad = [s for s in slugs if s not in PAGES]
    if bad:
        sys.exit('unknown page(s): %s\nknown: %s'
                 % (', '.join(bad), ', '.join(PAGES)))

    print('building %d page(s)' % len(slugs))
    built = [s for s in slugs if build(s)]

    if built:
        try:
            import optimize
            print('optimising images')
            for s in built:
                p = os.path.join(SITE, s + '.html')
                print('  %-22s %d <img> optimised' % (s, optimize.optimize(p)))
        except ImportError:
            print('optimize.py needs Pillow — skipping <img> pass')
            print('  pip3 install Pillow')

    print('sitemap.xml — %d urls' % sitemap())


if __name__ == '__main__':
    main(sys.argv[1:])
