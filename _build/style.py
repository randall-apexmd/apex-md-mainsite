# -*- coding: utf-8 -*-
"""The pinned token vocabulary for apexmd.com.

Read off the four handoffs that already share a system (Testosterone,
Genetics, Men's and Women's Optimal Health). The three outliers — Homepage
(Poppins/#E02424), Weight Loss (Jakarta/#e8232a) and Apex AI (#e11d2a) — are
normalised onto these values at build time by NORMALISE below.

Nothing here is invented. Every value appears in at least one handoff.
"""

# --- colour ------------------------------------------------------------
RED        = '#d30704'      # primary: CTAs, accents, rules, icons
RED_DARK   = '#a80503'      # button hover / pressed
RED_BRIGHT = '#ff5a4d'      # accent on dark grounds only
RED_TINT   = '#fdeeee'      # icon chips, callout panels
PINK       = '#c2185b'      # scoped: Women's Optimal Health section accent
PINK_DARK  = '#971146'

INK        = '#17140f'      # headings, primary text, dark grounds
BODY       = '#5f5952'      # paragraphs
MUTED      = '#7d766c'      # kickers, captions, legal
INK_SOFT   = '#33302b'      # footer links
BG         = '#ffffff'
BG_ALT     = '#faf8f6'      # alternating section bands
RULE       = '#e4dfd9'      # hairlines, section borders

# --- type --------------------------------------------------------------
# Archivo everywhere; JetBrains Mono for uppercase kickers; Playfair only for
# press wordmarks and pull quotes.
FONT_UI    = "Archivo, 'Helvetica Neue', Arial, sans-serif"
FONT_MONO  = "'JetBrains Mono', ui-monospace, monospace"
FONT_SERIF = "'Playfair Display', Georgia, serif"

GOOGLE_FONTS = (
    'https://fonts.googleapis.com/css2'
    '?family=Archivo:wght@400;500;600;700;800;900'
    '&family=JetBrains+Mono:wght@500;600;800'
    '&family=Playfair+Display:wght@700;900'
    '&display=swap'
)

# --- layout ------------------------------------------------------------
MAX      = '1400px'         # standard section container
MAX_WIDE = '1560px'         # full-bleed feature sections (Genetics uses this)
GUTTER   = 'clamp(20px,3.4vw,48px)'
RADIUS   = '14px'
RADIUS_L = '20px'
HEADER_H = '76px'

# The single mobile breakpoint. Four of the seven handoffs ship no mobile at
# all, so this is written once here and applied to every page rather than
# retrofitted per page.
BP_TABLET = 1024
BP_MOBILE = 760

# --- normalisation -----------------------------------------------------
# Applied to raw handoff CSS as a literal string substitution, longest key
# first. Case-insensitive on the hex values.
NORMALISE = {
    # accents from the three outlier pages -> house red
    '#e02424': RED,     # Homepage
    '#e8232a': RED,     # Weight Loss
    '#e11d2a': RED,     # Apex AI
    '#e01e1e': RED,     # Apex AI (second red in the same file)
    '#d60604': RED,     # Concierge — 2 hex points off the house red, which
    '#f0413f': RED,     # reads as a rendering fault rather than a choice
    '#b91c1c': RED_DARK,
    '#b01818': RED_DARK,
    # near-black grounds -> house ink
    '#17181a': INK,
    '#14110f': INK,
    '#0f0f10': INK,
    '#2b2b2e': BODY,
    # tinted grounds -> house alt ground
    '#fbf6f4': BG_ALT,
    '#faf7f6': BG_ALT,
    '#faf8f7': BG_ALT,
    '#f7f5f4': BG_ALT,
    '#fdecec': RED_TINT,
    '#fdf0ef': RED_TINT,
    # outlier font stacks -> Archivo
    'Poppins': 'Archivo',
    'Plus Jakarta Sans': 'Archivo',
}

# Fonts a single page needs on top of the house stack. Concierge sets its
# display italics in Fraunces; Blake asked for that page to stay as it is, so
# the face is kept and loaded only where it is used rather than folded onto
# Playfair for the sake of uniformity.
EXTRA_FONTS = {
    'concierge': '&family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,600;'
                 '0,9..144,700;1,9..144,400;1,9..144,600',
}

# Women's Optimal Health keeps its pink as a deliberate section accent, so its
# accent hexes are exempt from NORMALISE.
NORMALISE_EXEMPT = {'womens-health'}
