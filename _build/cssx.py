# -*- coding: utf-8 -*-
"""Lift inline style attributes out of a handoff page into a real stylesheet.

Why this exists
---------------
All seven handoffs were authored in a live-preview tool that writes every
declaration as an inline `style` attribute. Inline styles beat any stylesheet
rule short of `!important`, so a media query cannot reach them. That is the
structural reason four of the seven pages ship no mobile layout: it was never
possible to add one, not merely skipped.

So the build hoists each distinct inline style into a generated class. Once the
declarations live in a stylesheet, ordinary media queries work, the markup
shrinks by roughly the size of the style attributes, and the CSS caches across
pages instead of re-downloading per page.

The tool also emits the mobile layer. Every collapse below is derived from a
declaration actually present on the element — nothing is guessed:

  * a multi-column `grid-template-columns` collapses 4+->2 at tablet and ->1fr
    at mobile (an `auto-fit`/`minmax` track already reflows, so it is left be)
  * `flex-wrap:nowrap` becomes `wrap`
  * a `min-width` of 900px or more is dropped — this is the `min-width:1200px`
    page wrapper that the Testosterone and Genetics handoffs use, and it alone
    prevents those pages from ever rendering on a phone
  * padding and font-size above a threshold scale down proportionally

`style-hover` is the preview tool's non-standard hover attribute. It becomes a
real `:hover` rule.
"""
import re
import hashlib

import style as S

# ---------------------------------------------------------------- parsing

def split_decls(css):
    """Split a declaration list on top-level semicolons.

    Naive `css.split(';')` breaks `clamp(10px,1.02vw,13px)` and `rgba(0,0,0,.5)`
    apart mid-function, so track paren depth.
    """
    out, buf, depth = [], [], 0
    for ch in css:
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth = max(0, depth - 1)
        if ch == ';' and depth == 0:
            if buf:
                out.append(''.join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    if buf and ''.join(buf).strip():
        out.append(''.join(buf).strip())
    return [d for d in out if d]


def split_one(decl):
    """'padding: 0 12px' -> ('padding', '0 12px'). None if malformed."""
    i = decl.find(':')
    if i < 0:
        return None
    return decl[:i].strip().lower(), decl[i + 1:].strip()


def split_values(value):
    """Split a shorthand value on top-level whitespace, keeping functions whole."""
    out, buf, depth = [], [], 0
    for ch in value:
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth = max(0, depth - 1)
        if ch.isspace() and depth == 0:
            if buf:
                out.append(''.join(buf))
            buf = []
        else:
            buf.append(ch)
    if buf:
        out.append(''.join(buf))
    return out


def normalise(css, page):
    """Fold an outlier page's accent and font onto the house vocabulary."""
    if page in S.NORMALISE_EXEMPT:
        pairs = [(k, v) for k, v in S.NORMALISE.items()
                 if not k.startswith('#')]
    else:
        pairs = list(S.NORMALISE.items())
    for src, dst in sorted(pairs, key=lambda kv: -len(kv[0])):
        if src.startswith('#'):
            css = re.sub(re.escape(src), dst, css, flags=re.I)
        else:
            css = css.replace(src, dst)
    return css


# ------------------------------------------------------------ mobile layer

_PX = re.compile(r'^-?[\d.]+px$')

# Widest a fixed pixel dimension may be before it is forced fluid. 340 leaves
# room inside a 375px phone once the page gutter is taken off; 900 is the
# equivalent for the tablet breakpoint.
MOBILE_SAFE = 340
TABLET_SAFE = 900

def _scale_px(value, factor, floor=0):
    """Scale every bare px length in a shorthand, leaving other units alone."""
    parts = split_values(value)
    if not parts:
        return None
    out, touched = [], False
    for p in parts:
        if _PX.match(p):
            n = float(p[:-2])
            if n:
                scaled = max(floor, round(n * factor))
                if scaled != n:
                    touched = True
                out.append(f'{scaled:g}px')
                continue
        out.append(p)
    return ' '.join(out) if touched else None


def _collapse_grid(value, columns):
    """Reduce an explicit multi-track grid to `columns` tracks.

    `auto-fit`/`auto-fill` with `minmax` already reflows on its own, and
    `subgrid` inherits, so both are left untouched.
    """
    v = value.strip()
    low = v.lower()
    if 'subgrid' in low:
        return None

    if 'auto-fit' in low or 'auto-fill' in low:
        # These reflow the column COUNT on their own, which is why they look
        # safe — but `minmax(420px, 1fr)` still forces every column to be at
        # least 420px, so on a 375px phone the track is wider than the screen
        # and the row is clipped. `min(100%, 420px)` keeps the intended floor
        # on a wide viewport and yields to the container on a narrow one.
        m = re.search(r'minmax\(\s*([\d.]+)px\s*,', v, re.I)
        if m and float(m.group(1)) > MOBILE_SAFE:
            return re.sub(r'minmax\(\s*([\d.]+)px\s*,',
                          r'minmax(min(100%, \1px),', v, flags=re.I)
        return None

    m = re.match(r'^repeat\(\s*(\d+)\s*,(.+)\)$', v, re.I)
    if m:
        n = int(m.group(1))
        if n <= columns:
            return None
        return f'repeat({columns}, 1fr)'

    tracks = split_values(v)
    if len(tracks) <= columns or len(tracks) <= 1:
        return None
    return ' '.join(['1fr'] * columns) if columns > 1 else '1fr'


def mobile_rules(decls):
    """Return (tablet, mobile) declaration lists for one extracted class."""
    tablet, mobile = [], []
    props = {p for p, _ in decls}

    # A flex row with no declared wrap keeps `nowrap` (the CSS initial value)
    # and squeezes its children instead of breaking the line — on a phone that
    # turns a "Get Started Today" button into three stacked words. Wrapping is
    # a no-op when the children already fit, so this is safe to apply broadly;
    # `flex-direction:column` is already stacked and needs nothing.
    is_row = any(p == 'display' and 'flex' in v.lower() for p, v in decls)
    is_col = any(p == 'flex-direction' and 'column' in v.lower()
                 for p, v in decls)
    if is_row and not is_col and 'flex-wrap' not in props:
        mobile.append(('flex-wrap', 'wrap'))

    for prop, value in decls:
        if prop == 'grid-template-columns':
            t = _collapse_grid(value, 2)
            if t:
                tablet.append((prop, t))
            m = _collapse_grid(value, 1)
            if m:
                mobile.append((prop, m))

        elif prop == 'flex-wrap' and value.strip().lower() == 'nowrap':
            mobile.append((prop, 'wrap'))

        elif prop == 'min-width':
            # the desktop-only page wrapper: `min-width:1200px` on Testosterone
            # and Genetics. Anything that wide is a comp artefact, not a layout
            # intent, so drop it on both smaller breakpoints.
            v = value.strip()
            if _PX.match(v):
                n = float(v[:-2])
                if n >= 900:
                    tablet.append((prop, 'auto'))
                    mobile.append((prop, 'auto'))
                elif n > MOBILE_SAFE:
                    # narrower, but still wider than a phone — it would push
                    # the layout sideways and get clipped by the body
                    mobile.append((prop, 'auto'))

        elif prop == 'width':
            # Two separate problems share this property.
            #
            # A hard pixel width wider than the viewport: the comps were drawn
            # at 1440px, so cards and panels carry widths like 420px that a
            # 375px phone cannot show. They do not scroll (the body clips
            # them) — they get cut off, which is worse, because nothing
            # signals that content is missing.
            #
            # And a percentage over 100%, which is the handoffs' deliberate
            # full-bleed device: `width:150%` with `max-width:none` and a
            # negative margin, so a hero image spills past its column. That
            # reads as generous on a desktop and as broken on a phone.
            v = value.strip()
            if _PX.match(v):
                n = float(v[:-2])
                if n > MOBILE_SAFE:
                    mobile.append((prop, '100%'))
                    mobile.append(('max-width', '100%'))
                if n > TABLET_SAFE:
                    tablet.append((prop, '100%'))
                    tablet.append(('max-width', '100%'))
            elif v.endswith('%'):
                try:
                    if float(v[:-1]) > 100:
                        mobile.append((prop, '100%'))
                        mobile.append(('max-width', '100%'))
                except ValueError:
                    pass

        elif prop == 'max-width' and value.strip().lower() == 'none':
            # only ever paired with an over-100% width above; on its own it is
            # harmless, and 100% is the initial-ish behaviour anyway
            mobile.append((prop, '100%'))

        elif prop in ('margin', 'margin-left', 'margin-right'):
            # negative horizontal margins are the other half of the bleed
            # trick, and they push content under the phone's bezel
            parts = split_values(value)
            if any(_PX.match(x) and float(x[:-2]) < 0 for x in parts) or \
               any(x.endswith('%') and x.startswith('-') for x in parts):
                if prop == 'margin' and len(parts) >= 2:
                    # keep the vertical rhythm, drop only the horizontal bleed
                    top = parts[0]
                    bottom = parts[2] if len(parts) >= 3 else parts[0]
                    mobile.append((prop, '%s 0 %s' % (top, bottom)))
                else:
                    mobile.append((prop, '0'))

        elif prop == 'height':
            # once a fixed width becomes 100% the matching fixed height
            # distorts the image, so let it follow the aspect ratio
            v = value.strip()
            if _PX.match(v) and any(
                    p == 'width' and _PX.match(x.strip())
                    and float(x.strip()[:-2]) > MOBILE_SAFE
                    for p, x in decls):
                mobile.append((prop, 'auto'))

        elif prop in ('padding', 'padding-top', 'padding-bottom',
                      'padding-left', 'padding-right', 'gap',
                      'column-gap', 'row-gap', 'margin-top', 'margin-bottom'):
            # only worth scaling if something in there is genuinely large
            nums = [float(p[:-2]) for p in split_values(value) if _PX.match(p)]
            if nums and max(nums) >= 40:
                t = _scale_px(value, 0.68, floor=12)
                if t:
                    tablet.append((prop, t))
                m = _scale_px(value, 0.42, floor=10)
                if m:
                    mobile.append((prop, m))

        elif prop == 'font-size':
            v = value.strip()
            if _PX.match(v):
                n = float(v[:-2])
                if n >= 30:
                    tablet.append((prop, f'{max(24, round(n * 0.78)):g}px'))
                    mobile.append((prop, f'{max(20, round(n * 0.58)):g}px'))

        elif prop == 'transform' and 'scale(' in value.lower():
            # a scale() over 1 is a zoom-crop paired with object-fit:cover.
            # It only stays inside the layout while the container clips it;
            # several here do not, so the image spills past the screen edge.
            m = re.search(r'scale\(\s*([\d.]+)', value, re.I)
            if m and float(m.group(1)) > 1:
                mobile.append((prop, 'none'))

        elif prop == 'white-space' and value.strip().lower() == 'nowrap':
            mobile.append((prop, 'normal'))

        elif prop == 'position' and value.strip().lower() == 'absolute':
            # decorative cutouts bleed off-canvas on a phone; the handoffs all
            # position them absolutely against a desktop-width parent.
            pass

    return _dedupe(tablet), _dedupe(mobile)


def _dedupe(decls):
    """Last value wins per property, original order kept."""
    seen = {}
    for prop, value in decls:
        seen[prop] = value
    return list(seen.items())


# ------------------------------------------------------------- extraction

class Extractor:
    """Collect inline styles across a page and emit one stylesheet."""

    def __init__(self, page, prefix='x'):
        self.page = page
        self.prefix = prefix
        self.order = []          # class names, in first-seen order
        self.rules = {}          # class -> list[(prop, value)]
        self.hover = {}          # class -> list[(prop, value)]

    def _name(self, css):
        h = hashlib.sha1(css.encode('utf-8')).hexdigest()[:7]
        return f'{self.prefix}{h}'

    def add(self, css, hover_css=None):
        """Register a declaration block; return the class name for it."""
        css = normalise(css, self.page).strip().rstrip(';')
        if not css.strip():
            return None

        decls = []
        for d in split_decls(css):
            kv = split_one(d)
            if kv:
                decls.append(kv)
        if not decls:
            return None

        key = ';'.join(f'{p}:{v}' for p, v in decls)
        if hover_css:
            key += '||' + normalise(hover_css, self.page).strip()
        name = self._name(key)

        if name not in self.rules:
            self.rules[name] = decls
            self.order.append(name)
            if hover_css:
                hv = []
                for d in split_decls(normalise(hover_css, self.page)):
                    kv = split_one(d)
                    if kv:
                        hv.append(kv)
                if hv:
                    self.hover[name] = hv
        return name

    def stylesheet(self):
        """Render the collected rules, base then tablet then mobile."""
        def block(name, decls, indent=''):
            body = ';'.join(f'{p}:{v}' for p, v in decls)
            return f'{indent}.{name}{{{body}}}'

        base = [block(n, self.rules[n]) for n in self.order]
        hovers = [block(n + ':hover', self.hover[n])
                  for n in self.order if n in self.hover]

        tablet, mobile = [], []
        for n in self.order:
            t, m = mobile_rules(self.rules[n])
            if t:
                tablet.append(block(n, t, '  '))
            if m:
                mobile.append(block(n, m, '  '))

        out = [f'/* {self.page} — generated by _build/cssx.py. Do not edit. */']
        out += base
        if hovers:
            out.append('')
            out += hovers
        if tablet:
            out.append('')
            out.append(f'@media (max-width:{S.BP_TABLET}px){{')
            out += tablet
            out.append('}')
        if mobile:
            out.append('')
            out.append(f'@media (max-width:{S.BP_MOBILE}px){{')
            out += mobile
            out.append('}')
        return '\n'.join(out) + '\n'

    def stats(self):
        t = sum(1 for n in self.order if mobile_rules(self.rules[n])[0])
        m = sum(1 for n in self.order if mobile_rules(self.rules[n])[1])
        return {'classes': len(self.order), 'hover': len(self.hover),
                'tablet': t, 'mobile': m}


# ----------------------------------------------------------- page rewrite

_TAG = re.compile(r'<(?!/)([a-zA-Z][\w-]*)((?:"[^"]*"|\'[^\']*\'|[^>"\'])*)>')
_STYLE = re.compile(r'\sstyle="([^"]*)"')
_HOVER = re.compile(r'\sstyle-hover="([^"]*)"')
_CLASS = re.compile(r'\sclass="([^"]*)"')


def rewrite(html, ex):
    """Replace every style attribute in `html` with a generated class."""
    out, pos = [], 0
    for m in _TAG.finditer(html):
        tag, attrs = m.group(1), m.group(2)
        sm = _STYLE.search(attrs)
        if not sm:
            continue

        hm = _HOVER.search(attrs)
        name = ex.add(sm.group(1), hm.group(1) if hm else None)

        new = _STYLE.sub('', attrs, count=1)
        new = _HOVER.sub('', new)
        if name:
            cm = _CLASS.search(new)
            if cm:
                merged = f'{cm.group(1)} {name}'.strip()
                new = new[:cm.start()] + f' class="{merged}"' + new[cm.end():]
            else:
                new = new.rstrip() + f' class="{name}"'

        out.append((m.start(), m.end(), f'<{tag}{new}>'))

    for start, end, repl in reversed(out):
        html = html[:start] + repl + html[end:]
    return html, len(out)
