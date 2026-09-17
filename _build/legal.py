# -*- coding: utf-8 -*-
"""Render the legal pages: /privacy-policy and /terms-and-conditions.

    python3 _build/build.py privacy-policy terms-and-conditions

The copy is approved legal text and Blake asked for it VERBATIM. It lives in
legal/<slug>.html, lifted from the live apexmd.com page by legal/extract.py
(markup stripped to p/ol/li/strong/em/a, every word kept). This module only
changes markup around those words — it never adds, drops or reorders one.
render() checks that on every build and refuses to write a page whose word
sequence differs from the source file.

    Privacy Policy        6,842 words  (live: elementor-element-1de46a1)
    Terms of Service     13,102 words  (live: elementor-element-2757fb7)

To refresh after the live copy changes:

    curl -sL https://apexmd.com/privacy-policy -o /tmp/p.html
    python3 _build/legal/extract.py /tmp/p.html elementor-element-1de46a1 \\
        _build/legal/privacy-policy.html
"""
import html as html_lib
import re

# slug -> (title, description, page heading as it appears in the copy)
LEGAL = {
    'privacy-policy': (
        'Privacy Policy | Apex MD',
        'How Apex MD collects, uses, discloses and protects your information.',
        'Privacy Policy',
    ),
    'terms-and-conditions': (
        'Terms of Service | Apex MD',
        'The terms that govern your use of Apex MD and its services.',
        'Terms of Service',
    ),
}

# The source is all <p>: the live page has no heading markup at all. These are
# the paragraphs that read as headings, named by their exact text so a change
# in the copy shows up as a warning rather than a silently mis-styled page.
HEADINGS = {
    'privacy-policy': {
        'h2': [
            'Introduction',
            'Information We Collect About You and How It’s Collected',
            'III. How We Use Your Information',
            'Disclosure of Your Information',
            'Options About How We Use And Disclose Your Information',
            'Data Security',
            'VII. Third-Party Platforms',
            'VIII. No Services To Persons Under The Age of 18',
            'California Resident Privacy Rights',
            'Revisions to Our Privacy Policy',
            'Contact Information',
            'APPLICATIONS',
            'Functional Medicine Concierge Program',
        ],
        'h3': [
            'Information About You and Your Health Care Treatment and Payment.',
            'Information You Give to Us.',
            'Information We Receive From Other Sources.',
            'ADDITIONAL DATA USE, ANALYTICS, AND PARTNER SHARING',
            'Categories of Third-Parties',
            'III. California Resident Privacy Rights',
            'Privacy Officer',
        ],
    },
    'terms-and-conditions': {
        'h2': [],
        'h3': [
            'Concierge Program:',
            'Program Overview',
            'Refund Policy',
            'Medical and Emergency Disclaimer',
            'Scope of Practice',
            'No Guarantee of Results',
            'Patient Responsibility and Continuity of Care',
        ],
    },
}

ROMAN = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X',
         'XI', 'XII', 'XIII', 'XIV', 'XV', 'XVI', 'XVII', 'XVIII', 'XIX', 'XX',
         'XXI', 'XXII', 'XXIII', 'XXIV', 'XXV', 'XXVI', 'XXVII', 'XXVIII',
         'XXIX', 'XXX', 'XXXI', 'XXXII', 'XXXIII', 'XXXIV', 'XXXV', 'XXXVI',
         'XXXVII', 'XXXVIII', 'XXXIX', 'XL', 'XLI', 'XLII', 'XLIII', 'XLIV']

CSS = """
.lg { max-width: 760px; margin: 0 auto; padding: 72px var(--apex-gutter) 112px; }
.lg-kicker { font: 800 12px/1 var(--apex-font-mono); letter-spacing: .16em;
             text-transform: uppercase; color: var(--apex-red); }
.lg h1 { margin: 16px 0 14px; font-size: clamp(36px, 6vw, 56px); font-weight: 900;
         line-height: 1.02; letter-spacing: -.02em; }
.lg-meta { margin: 0; font: 500 15px/1.5 var(--apex-font-ui); color: var(--apex-muted); }
.lg-meta span + span::before { content: "·"; margin: 0 10px; color: var(--apex-rule); }
.lg-body { margin-top: 40px; padding-top: 40px; border-top: 1px solid var(--apex-rule);
           font-size: 16px; line-height: 1.7; color: var(--apex-body); }
.lg-body p { margin: 0 0 18px; overflow-wrap: anywhere; }
.lg-body strong { color: var(--apex-ink-soft); }
.lg-body a { text-decoration: underline; text-underline-offset: 2px; }
.lg-body h2 { margin: 52px 0 16px; font-size: 24px; line-height: 1.25; font-weight: 800;
              color: var(--apex-ink); letter-spacing: -.01em; }
.lg-body h3 { margin: 32px 0 12px; font-size: 18px; line-height: 1.35; font-weight: 700;
              color: var(--apex-ink); }
.lg-body ol { margin: 32px 0 12px; padding: 0; list-style: none; font-size: 18px;
              font-weight: 700; line-height: 1.35; color: var(--apex-ink); }
/* each of these is its own one-item <ol> on the live page, so the browser
   numbered every one "1." — the numbers were never part of the copy */
.lg-body > :first-child { margin-top: 0; }
.lg-alert { padding: 16px 20px; border-left: 3px solid var(--apex-red);
            background: var(--apex-red-tint); color: var(--apex-ink); font-weight: 600;
            border-radius: 0 8px 8px 0; }

/* Terms is an outline: I / A / 1 markers, each its own paragraph on the live page */
.lg-sec { margin: 52px 0 18px; padding-top: 28px; border-top: 1px solid var(--apex-rule); }
.lg-sec .lg-mark { display: block; margin-bottom: 10px; font: 800 12px/1 var(--apex-font-mono);
                   letter-spacing: .16em; color: var(--apex-red); }
.lg-sec p { margin: 0; color: var(--apex-ink-soft); }
.lg-item { display: grid; grid-template-columns: 28px 1fr; gap: 0 8px; margin: 0 0 18px; }
.lg-item .lg-mark { font: 700 13px/1.75 var(--apex-font-mono); color: var(--apex-red); }
.lg-item > p { margin: 0; }
.lg-l3 { margin-left: 36px; }
@media (max-width: 760px) {
  .lg { padding-top: 48px; padding-bottom: 80px; }
  .lg-body { font-size: 15.5px; }
  .lg-body h2 { font-size: 21px; }
  .lg-l3 { margin-left: 16px; }
}
"""


def words(fragment):
    # inline tags join words, block tags separate them
    fragment = re.sub(r'</?(?:a|strong|em|u|span)\b[^>]*>', '', fragment)
    text = html_lib.unescape(re.sub(r'<[^>]+>', ' ', fragment))
    return text.split()


def _text(p):
    return html_lib.unescape(re.sub(r'<[^>]+>', '', p)).strip()


def render(slug, source):
    """Return (header_html, body_html, warnings) for one legal page."""
    title, _desc, heading = LEGAL[slug]
    warnings = []
    blocks = [b for b in source.split('\n') if b.strip()]

    # Lift the heading, "Apex MD" and "Last updated" lines out of the flow and
    # into the page header. They are the same words, shown once.
    top, blocks = blocks[:3], blocks[3:]
    top_text = [_text(b) for b in top]
    updated = next((t for t in top_text if t.startswith('Last updated:')), '')
    if sorted(top_text) != sorted([heading, 'Apex MD', updated]):
        raise SystemExit('legal.py: %s — expected the copy to open with the '
                         'heading, "Apex MD" and "Last updated", got %r'
                         % (slug, top_text))
    header = ('<div class="lg-kicker">Legal</div>\n'
              '<h1>%s</h1>\n<p class="lg-meta"><span>Apex MD</span><span>%s</span></p>'
              % (html_lib.escape(heading), html_lib.escape(updated)))

    heads = HEADINGS.get(slug, {})
    level_of = {}
    for lvl, names in heads.items():
        for n in names:
            level_of[n] = lvl
    seen = set()

    out = []
    next_roman = 0
    i = 0
    while i < len(blocks):
        b = blocks[i]
        m = re.fullmatch(r'<p>(.*)</p>', b)
        t = _text(b) if m else ''

        # an outline marker on its own line, followed by the paragraph it labels
        is_marker = m and re.fullmatch(r'[IVXL]+|[A-Z]|\d{1,2}', t)
        if is_marker and slug == 'terms-and-conditions' and i + 1 < len(blocks):
            nxt = blocks[i + 1]
            if next_roman < len(ROMAN) and t == ROMAN[next_roman]:
                next_roman += 1
                out.append('<div class="lg-sec" id="section-%s"><span class="lg-mark">%s</span>%s</div>'
                           % (t.lower(), t, nxt))
            else:
                cls = 'lg-item lg-l3' if t.isdigit() else 'lg-item'
                out.append('<div class="%s"><span class="lg-mark">%s</span>%s</div>'
                           % (cls, t, nxt))
            i += 2
            continue

        if m and t in level_of:
            lvl = level_of[t]
            seen.add(t)
            out.append('<%s>%s</%s>' % (lvl, m.group(1).strip(), lvl))
        elif m and re.search(r'MEDICAL EMERGENCY', t) and t.isupper() and len(out) < 3:
            out.append('<p class="lg-alert">%s</p>' % m.group(1))
        else:
            out.append(b)
        i += 1

    for n in level_of:
        if n not in seen:
            warnings.append('heading no longer in the copy: %r' % n)

    body = '\n'.join(out)
    # plain-text email addresses become mailto links; the address is unchanged
    body = re.sub(r'(?<![\w@">])([\w.+-]+@apexmd\.com)(?![\w"<])',
                  r'<a href="mailto:\1">\1</a>', body)

    # The only permitted difference is that the three opening lines now sit in
    # the page header, where "Apex MD" always follows the heading.
    lead = [w for b in top for w in words(b)]
    if words(source) != lead + words(body):
        raise SystemExit('legal.py: %s — rendered words differ from the source. '
                         'Refusing to write a page that alters legal copy.' % slug)
    return header, body, warnings
