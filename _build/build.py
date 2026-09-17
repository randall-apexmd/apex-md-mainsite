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
import html as html_lib
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cssx
import images
import legal
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
# Pages written by hand in _build/pages/<slug>.html (+ .css), rather than
# assembled from a design handoff. Their copy and photography come from the
# live apexmd.com page of the same name.
#
#   slug -> (asset source dir under _src, nav section, title, description)
HAND = {
    'about-us': ('about', 'about',
                 'About Apex MD — Physician-Led Medical Wellness',
                 'Apex MD combines licensed providers, advanced diagnostics and '
                 'personalized programs to help you optimize weight, hormones, '
                 'performance and longevity.'),
}


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


# A page whose headline lives only inside a hero image has no <h1> at all —
# search engines and screen readers both see an untitled page. Apex MD AI is
# the only one: its "One Platform. Complete Clarity." is baked into hero.jpg.
# The text is the image's own, so this adds nothing the page does not already
# say; it just makes it readable.
HEADING = {
    'apex-md-ai': 'Apex MD AI — One Platform. Complete Clarity.',
}


# Sections whose desktop layout is absolute positioning against a wide parent.
# On a phone those images land on top of the text. The generic mobile layer
# cannot unpick them safely — most absolute elements are badges and labels
# that should stay exactly where they are — so each one is named here, by the
# start of the handoff's own inline style, and given a class that the .m-*
# rules in apex.css act on below 760px.
#
#   m-panel       a side image panel: made a normal block, 260px tall
#   m-static      a feature image: dropped back into the flow, full width
#   m-hide        a desktop-only mask or decorative layer
#   m-autoheight  a fixed-height stage that must grow to fit stacked content
#   m-pad-top-48  a card whose top padding is the landing space for a badge
#                 overlapping it from above; the generic padding scale-down
#                 removes that space and the badge lands on the heading
#   img-bleed     (all widths) an image meant to bleed past its card, which
#                 the house `img { max-width:100% }` reset would squash
MOBILE_FIX = {
    'glp-1-program': [
        ('background:#f7f7f8;border-radius:18px;padding:48px 24px 0', 'm-pad-top-48'),
    ],
    'womens-optimal-health': [
        ('position:absolute;top:0;right:-10%;height:100%;width:auto', 'img-bleed'),
        ('position:relative;overflow:hidden;background:#ffffff;height:clamp(460px', 'm-autoheight'),
        ('position:absolute;top:0;bottom:0;left:46%', 'm-panel'),
        ('position:absolute;top:0;bottom:0;left:0;width:46%;background:#ffffff', 'm-hide'),
        ('position:absolute;top:0;bottom:0;right:0;width:22%;background:linear-gradient', 'm-hide'),
        ('position:absolute;top:44px;bottom:44px;left:calc(50% + 70px)', 'm-panel'),
    ],
    'apex-md-ai': [
        ('position: absolute; left: 36%; top: -6%; width: 76%', 'm-hide'),
        ('position: absolute; left: 0; top: 50%; transform: translateY(-50%); width: 60%', 'm-static'),
        ('position: absolute; right: -53%; bottom: -6%', 'm-hide'),
    ],
}


# Handoff markup replaced wholesale by a part from _build/parts at build time.
# slug -> [(regex matching the handoff block, part filename)]
PART_SWAPS = {
    # the Tirzepatide comparison was a flat PNG, unreadable on a phone
    'glp-1-program': [
        (r'<div style="border-radius:20px;overflow:hidden;border:1px solid #ececed;'
         r'background:#fff;">\s*<img src="assets/tirz-comparison\.png"[^>]*>\s*</div>',
         'glp-comparison.html'),
    ],
}

# Handoff blocks removed outright. Men's and Women's each carried a strip
# ("HSA / FSA eligible · no membership required · Patient Login") above
# their own header; with the shared header in place it only repeated Patient
# Login, and on a phone it was a tall two-line block before any content.
_HSA_STRIP = (r'<div style="background:#(?:d30704|c2185b);color:#fff;display:flex;'
              r'justify-content:space-between;align-items:center;gap:24px;'
              r'padding:9px 48px;[^"]*">.*?</div>')
STRIP_BLOCKS = {
    'mens-optimal-health':   [_HSA_STRIP],
    'womens-optimal-health': [_HSA_STRIP],
}

# Placeholders the handoffs left unfilled, filled with the matching image from
# the live apexmd.com page (pulled 2026-09-11, saved into _src/<handoff>/assets
# as live-*.jpg). slug -> [(regex for the placeholder, replacement markup)].
# An empty replacement removes the block.
_COVER = 'position:absolute;inset:0;width:100%;height:100%;object-fit:cover'
IMAGE_FILL = {
    'glp-1-program': [
        # Pablo Lopez's card: the slot plus its dashed "BEFORE / AFTER" label
        (r'<image-slot id="trans-1"[^>]*></image-slot><span style="position:absolute;'
         r'bottom:14px;left:14px;font-family:ui-monospace[^"]*">BEFORE / AFTER</span>',
         '<img src="assets/live-pablo-lopez.jpg" alt="Pablo Lopez before and after" '
         'style="width:100%;height:100%;object-fit:cover;display:block;">'),
        # "Member Result" is a template card with no real patient behind it
        # ("Add your patient's quote here"); no eighth photo exists live
        (r'<div style="flex:0 0 calc\(\(100% - 44px\)/3\);[^"]*"><div style="position:'
         r'relative;height:300px;"><image-slot id="trans-8".*?</div></div></div>', ''),
    ],
    'mens-optimal-health': [
        # hero-dna.png shipped with the handoff and nothing referenced it; it
        # is the red helix artwork this slot asks for. Framed on the helix,
        # which sits in the right-hand third of a landscape image.
        (r'<image-slot id="apex-moh-dna"[^>]*></image-slot>',
         '<img src="assets/hero-dna.png" alt="DNA helix" style="width:100%;'
         'height:100%;object-fit:cover;object-position:78% center;display:block">'),
    ],
    'genetics': [
        (r'<div class="img-placeholder" id="di2"[^>]*>[^<]*</div>',
         '<img src="assets/live-di-potential.jpg" alt="Member reviewing his genetic '
         'results" style="%s">' % _COVER),
        (r'<div class="img-placeholder"[^>]*>Member reading results on a tablet</div>',
         '<img src="assets/live-ep-portal-results.jpg" alt="Member reading her results '
         'on a tablet" style="%s">' % _COVER),
        (r'<div class="img-placeholder"[^>]*>Member checking her action steps on her phone</div>',
         '<img src="assets/live-ep-action-steps.jpg" alt="Member checking her action '
         'steps on her phone" style="%s">' % _COVER),
        (r'<div class="img-placeholder"[^>]*>Shield and padlock representing secure data</div>',
         '<img src="assets/live-ep-hipaa.jpg" alt="Shield and padlock representing '
         'secure data" style="%s">' % _COVER),
    ],
}

# Page-scoped CSS appended after the handoff's own <style>, so it wins ties.
EXTRA_CSS = {
    # two physicians in a grid drawn for three left an empty third column;
    # below 1025px the page's own two-column and slider rules take over
    'concierge': '@media (min-width:1025px){.docs-grid{grid-template-columns:'
                 'repeat(2,minmax(0,1fr));max-width:900px;margin-left:auto;'
                 'margin-right:auto}}',
}


def tag_by_style(body, rules):
    """Add a class to each tag whose inline style starts with a given prefix.

    Merges into an existing class attribute rather than adding a second one —
    a browser keeps only the first of two, which would silently drop the tag.
    """
    if not rules:
        return body, 0
    edits = []
    for m in cssx._TAG.finditer(body):
        attrs = m.group(2)
        sm = re.search(r'\sstyle="([^"]*)"', attrs)
        if not sm:
            continue
        add = [cls for prefix, cls in rules if sm.group(1).startswith(prefix)]
        if not add:
            continue
        cm = re.search(r'\sclass="([^"]*)"', attrs)
        if cm:
            attrs = (attrs[:cm.start()] + ' class="%s %s"' % (cm.group(1), ' '.join(add))
                     + attrs[cm.end():])
        else:
            attrs = ' class="%s"' % ' '.join(add) + attrs
        edits.append((m.start(), m.end(), '<%s%s>' % (m.group(1), attrs)))
    for start, end, repl in reversed(edits):
        body = body[:start] + repl + body[end:]
    return body, len(edits)


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


def design_props(body):
    """Default values of a canvas handoff's props, read from its data-props.

    The `.dc.html` exports are templates: `{{ accent }}` is a live binding
    that support.js fills from the component's declared defaults at runtime.
    The defaults travel with the file as JSON on the `<x-dc data-props>`
    element, so they can be resolved at build time instead.
    """
    m = re.search(r'data-props="([^"]*)"', body)
    if not m:
        return {}
    try:
        declared = json.loads(html_lib.unescape(m.group(1)))
    except ValueError:
        return {}
    props = {k: v['default'] for k, v in declared.items()
             if isinstance(v, dict) and 'default' in v}
    # the GLP-1 canvas declares `accentColor` but its template reads `accent`
    if 'accent' not in props and 'accentColor' in props:
        props['accent'] = props['accentColor']
    return props


def clean_design_tool(body, slug):
    """Resolve the authoring tool's template, then strip its scaffolding.

    Three of the handoffs are `.dc.html` canvas files that expect `support.js`
    to render them. We ship static HTML instead, so:

      {{ prop }}   filled from the component's declared default. An earlier
                   version deleted these as leftovers. They are not: Apex AI
                   uses `{{ accent }}` 62 times for button fills, icon
                   strokes and section grounds, and GLP-1 sets its whole
                   `--accent` from one. Deleting them left white-on-white
                   buttons and icons that painted nothing.
      <sc-if>      a conditional, kept or dropped by its prop's default
      onClick/ref  the GLP-1 carousel's handlers, turned into data hooks
                   that apex.js wires up
      <helmet>     holds the <link>/<style> the shell already provides
      <x-dc>       the canvas wrapper; an unknown element defaults to
                   display:inline, so it reports zero height and its
                   whitespace prints as stray inline text
      <image-slot> a deliberate image placeholder the designer left unfilled

    image-slot becomes a visible dashed box captioned with its intended
    subject, so an unfinished image reads as unfinished instead of as an
    empty gap nobody notices.
    """
    counts = {'helmet': 0, 'x-dc': 0, 'sc-if': 0, 'image-slot': 0, 'props': 0,
              'slot-img': 0}
    props = design_props(body)

    def truthy(v):
        return v not in (None, False, 0, '', 'false', 'False')

    def resolve_if(m):
        cond = re.search(r'value="\{\{\s*(\w+)\s*\}\}"', m.group(1))
        return m.group(2) if cond and truthy(props.get(cond.group(1))) else ''

    body, n = re.subn(r'<sc-if\b([^>]*)>(.*?)</sc-if>', resolve_if, body,
                      flags=re.S | re.I)
    counts['sc-if'] = n

    body = re.sub(r'\bref="\{\{\s*setTrack\s*\}\}"', 'data-carousel-track', body)
    body = re.sub(r'\bonClick="\{\{\s*prev\s*\}\}"', 'data-carousel-prev', body,
                  flags=re.I)
    body = re.sub(r'\bonClick="\{\{\s*next\s*\}\}"', 'data-carousel-next', body,
                  flags=re.I)

    def fill(m):
        val = props.get(m.group(1))
        if val is None or isinstance(val, (dict, list)):
            return m.group(0)
        counts['props'] += 1
        val = 'true' if val is True else 'false' if val is False else str(val)
        return cssx.normalise(html_lib.escape(val, quote=True), slug)

    body = re.sub(r'\{\{\s*(\w+)\s*\}\}', fill, body)

    body, n = re.subn(r'<helmet\b.*?</helmet>', '', body, flags=re.S | re.I)
    counts['helmet'] = n

    body, n = re.subn(r'</?x-dc\b[^>]*>', '', body, flags=re.I)
    counts['x-dc'] = n

    def slot(m, closed=True):
        """Render one <image-slot>. `closed` means the match consumed the
        closing tag too, so the replacement has to be a complete element."""
        attrs = m.group(1)
        cls = re.search(r'class="([^"]*)"', attrs)
        label = re.search(r'placeholder="([^"]*)"', attrs)
        src = re.search(r'src="([^"]*)"', attrs)
        # A slot can carry its image already — the Men's "Decreased muscle"
        # card does. Treating every slot as empty threw that picture away and
        # drew a dashed "image needed" box over a photo that shipped with the
        # handoff.
        if src:
            counts['slot-img'] += 1
            # the slot's own sizing, not absolute positioning: these
            # containers are not all positioned, and an absolute image in an
            # unpositioned parent escapes to the page and covers whatever it
            # lands on (it covered the entire Men's hero)
            return ('<img src="%s" alt="%s" class="%s" style="width:100%%;'
                    'height:100%%;object-fit:cover;display:block">'
                    % (src.group(1), label.group(1) if label else '',
                       cls.group(1) if cls else ''))
        counts['image-slot'] += 1
        # keep the slot's own sizing, or the box collapses to its min-height
        # and leaves the rest of the card showing as bare grey
        style = re.search(r'style="([^"]*)"', attrs)
        return ('<div class="%s img-todo" data-todo="%s" style="%s">%s'
                % (cls.group(1) if cls else '',
                   label.group(1) if label else 'image',
                   style.group(1) if style else 'width:100%;height:100%',
                   '</div>' if closed else ''))

    # Replace the whole element, opening and closing tag together. Handling
    # them separately broke the markup the moment a slot became an <img>: the
    # orphaned </image-slot> still turned into a </div>, which closed the
    # surrounding grid early and threw the following card out of it.
    body = re.sub(r'<image-slot\b([^>]*)>\s*</image-slot>',
                  lambda m: slot(m, True), body, flags=re.I)
    body = re.sub(r'<image-slot\b([^>]*)>',
                  lambda m: slot(m, False), body, flags=re.I)
    body = re.sub(r'</image-slot>', '</div>', body, flags=re.I)

    # Whatever is still standing has no declared default, so it is an
    # expression rather than a prop, and would print as literal text.
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
            key = '%s/%s' % (slug, os.path.splitext(name)[0] + '.webp')
            out, b, a = images.optimise(src, dst_dir, name, key)
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

    for pat in STRIP_BLOCKS.get(slug, []):
        body, k = re.subn(pat, '', body, count=1, flags=re.S)
        if not k:
            print('    STRIP_BLOCKS rule no longer matches: %s…' % pat[:60])
    for pat, repl in IMAGE_FILL.get(slug, []):
        body, k = re.subn(pat, lambda _m: repl, body, count=1, flags=re.S)
        if not k:
            print('    IMAGE_FILL rule no longer matches: %s…' % pat[:60])
    for pat, part in PART_SWAPS.get(slug, []):
        markup = re.sub(r'<!--.*?-->', '', read(os.path.join(PARTS, part)), flags=re.S)
        body, k = re.subn(pat, lambda _m: markup, body, count=1, flags=re.S)
        if not k:
            print('    PART_SWAPS rule for %s no longer matches' % part)

    # Normalise the whole body, not just the style attributes. The handoffs
    # carry their accent in three more places cssx never sees: inline SVG
    # `fill=`/`stroke=` presentation attributes, `var(--accent,#e8232a)`
    # fallbacks, and the design tool's escaped JSON metadata blocks. Miss
    # these and every icon on the Homepage and Weight Loss pages keeps its
    # old red while the text around it turns house red.
    body = cssx.normalise(body, slug)
    body, tool = clean_design_tool(body, slug)

    # Men's and Women's pin a product bar to the bottom of the viewport. Tag it
    # so apex.css can compact it on phones, where its title and price wrap it
    # to 164px — a fifth of the screen, for the whole visit.
    body, _ = tag_by_style(body, [('position:fixed;left:0;right:0;bottom:0;', 'sticky-cta')])
    fixes = MOBILE_FIX.get(slug, [])
    unmatched = [p for p, _ in fixes if 'style="%s' % p not in body]
    body, _ = tag_by_style(body, fixes)
    for p in unmatched:
        print('    MOBILE_FIX rule no longer matches — handoff changed? %s…' % p[:60])

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

    pcss = page_style(raw, slug) + EXTRA_CSS.get(slug, '')
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
        header=chrome('header.html', active, slug)
               + ('\n<h1 class="vh">%s</h1>' % HEADING[slug]
                  if slug in HEADING else ''),
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

    html = version_assets(html)
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


def build_legal(slug):
    """A legal page: verbatim copy from legal/<slug>.html in a plain long-form
    template, with the same header and footer as every other page."""
    title_, desc, _heading = legal.LEGAL[slug]
    source = read(os.path.join(BUILD, 'legal', slug + '.html'))
    head, body, warnings = legal.render(slug, source)

    write(os.path.join(SITE, 'assets', 'css', 'legal.css'), legal.CSS.lstrip())
    html = SHELL.format(
        title=title_,
        desc=desc.replace('"', '&quot;'),
        url_path='/' + slug,
        fonts=S.GOOGLE_FONTS,
        slug=slug,
        page_css='',
        header=chrome('header.html', None, slug),
        footer=chrome('footer.html', None, slug),
        body='<article class="lg">\n%s\n<div class="lg-body">\n%s\n</div>\n</article>'
             % (head, body),
    )
    html = html.replace('/assets/css/%s.css' % slug, '/assets/css/legal.css')
    # no social card of its own; share the homepage's
    html = html.replace('/assets/og/%s.jpg' % slug, '/assets/og/index.jpg')
    html = version_assets(html)
    write(os.path.join(SITE, slug + '.html'), html)

    print('  %-22s %d words, verbatim' % (slug, len(legal.words(source))))
    for w in warnings:
        print('    ' + w)
    return True


def build_hand(slug):
    """Stamp a hand-authored page from _build/pages/ into site/."""
    src_dir, active, page_title, page_desc = HAND[slug]
    body = re.sub(r'^\s*<!--.*?-->\s*', '', read(os.path.join(BUILD, 'pages', slug + '.html')),
                  flags=re.S)
    body, links = relink(body, slug)

    css_dst = os.path.join(SITE, 'assets', 'css', slug + '.css')
    write(css_dst, read(os.path.join(BUILD, 'pages', slug + '.css')))

    # copy the photography, then run it through the same optimiser the
    # handoff pages use (resize, WebP, width/height, loading hints)
    img_dir = os.path.join(SITE, 'assets', 'images', slug)
    src_assets = os.path.join(SRC, src_dir, 'assets')
    copied, before, after = 0, 0, 0
    if os.path.isdir(src_assets):
        if not os.path.isdir(img_dir):
            os.makedirs(img_dir)
        for name in sorted(os.listdir(src_assets)):
            if name.startswith('.') or '/assets/images/%s/%s' % (slug, name) not in body:
                continue
            s_path = os.path.join(src_assets, name)
            new_name, b, a = images.optimise(s_path, img_dir, name,
                                             '%s/%s' % (slug, name))
            before += b
            after += a
            if new_name != name:
                body = body.replace('/assets/images/%s/%s' % (slug, name),
                                    '/assets/images/%s/%s' % (slug, new_name))
            copied += 1

    missing = [m for m in re.findall(r'/assets/images/%s/([^"\s]+)' % slug, body)
               if not os.path.isfile(os.path.join(img_dir, m))]

    html = SHELL.format(
        title=page_title,
        desc=page_desc.replace('"', '&quot;'),
        url_path='/' + slug,
        fonts=S.GOOGLE_FONTS,
        slug=slug,
        page_css='',
        header=chrome('header.html', active, slug),
        footer=chrome('footer.html', None, slug),
        body=body.strip(),
    )
    html = html.replace('/assets/og/%s.jpg' % slug, '/assets/og/index.jpg')
    html = version_assets(html)
    write(os.path.join(SITE, slug + '.html'), html)

    print('  %-22s %3d links | %2d img %s -> %s'
          % (slug, sum(links.values()), copied,
             images.human(before), images.human(after)))
    if missing:
        print('    MISSING asset(s): %s' % ', '.join(sorted(set(missing))))
    return True


def asset_version(rel):
    """Short content hash for an asset under site/, or None if missing."""
    path = os.path.join(SITE, rel.lstrip('/'))
    if not os.path.isfile(path):
        return None
    with open(path, 'rb') as fh:
        return hashlib.sha1(fh.read()).hexdigest()[:8]


def version_assets(html):
    """Stamp ?v=<content hash> on every stylesheet and script this page loads.

    vercel.json serves /assets/ with `max-age=31536000, immutable`, which is
    correct only if the URL changes when the bytes do. It did not: the files
    have stable names, so a returning browser held the previous stylesheet for
    a year and rendered the header logo at its intrinsic 499x102 instead of
    the 34px the CSS asks for. Versioning the URL is what makes the immutable
    header honest.
    """
    def sub(m):
        attr, path = m.group(1), m.group(2)
        v = asset_version(path)
        return '%s="%s?v=%s"' % (attr, path, v) if v else m.group(0)

    return re.sub(r'\b(href|src)="(/assets/(?:css|js)/[^"?]+)"', sub, html)


def sitemap():
    """Write sitemap.xml for the pages that exist.

    robots.txt already advertises it. Only built pages are listed — a sitemap
    that names a URL which 404s is worse than no sitemap, because Search
    Console reports it as an error against the whole domain.
    """
    today = datetime.date.today().isoformat()
    urls = []
    for slug in sorted(list(PAGES) + list(HAND) + list(legal.LEGAL)):
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
    known = list(PAGES) + list(HAND) + list(legal.LEGAL)
    slugs = argv or known
    bad = [s for s in slugs if s not in known]
    if bad:
        sys.exit('unknown page(s): %s\nknown: %s'
                 % (', '.join(bad), ', '.join(known)))

    print('building %d page(s)' % len(slugs))
    for s in slugs:
        if s in legal.LEGAL:
            build_legal(s)
        elif s in HAND:
            build_hand(s)
    built = [s for s in slugs if s in PAGES and build(s)]
    built += [s for s in slugs if s in HAND]

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

    nf = os.path.join(SITE, '404.html')
    if os.path.isfile(nf):
        src = read(nf)
        stamped = version_assets(re.sub(r'(/assets/(?:css|js)/[^"?]+)\?v=[0-9a-f]+',
                                        r'\1', src))
        if stamped != src:
            write(nf, stamped)
            print('404.html — asset versions stamped')

    print('sitemap.xml — %d urls' % sitemap())


if __name__ == '__main__':
    main(sys.argv[1:])
