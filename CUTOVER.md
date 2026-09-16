# Cutting apexmd.com over to this build

Written 2026-09-08. Facts here were read off the live domain that day —
re-check them before you actually pull the trigger.

## Where things stand today

| | |
|---|---|
| Live site | WordPress, Apache, PHP 8.3 at `107.180.96.144` |
| Nameservers | `ns1/ns2.namebrightdns.com` |
| Email | Google Workspace — `MX → smtp.google.com` |
| Live URLs | 76 (65 of them pages) |
| Rebuilt here | 7 |

## The one thing that can actually break something

**Connect the domain with an A record, not by moving nameservers.**

Vercel offers both. They are not equivalent here:

- **A record → `76.76.21.21`** (plus `CNAME www → cname.vercel-dns.com`).
  DNS stays at NameBright, your MX records stay exactly where they are, and
  **email keeps working.**
- **Nameservers → Vercel.** Your MX records do not come along. Google
  Workspace stops delivering until they are recreated by hand. Do not do this.

Nothing else in the cutover is dangerous. `ehr.apexmd.com` and
`formmac.apexmd.com` are separate subdomains — changing the root A record does
not touch them.

## The real blocker: 58 pages have nowhere to go

Seven pages are rebuilt. The live site serves 65. Point the root at Vercel
today and the rest 404, including `/faq/`, `/peptides/`, `/supplements/`,
`/hormone-therapy/`, `/microdosing/`, `/contact-us/`, `/privacy-policy/`,
`/terms-and-conditions/`, `/primary-care/` and `/nutrition-coaching/`.

`vercel.json` already redirects the 16 old slugs that map onto a rebuilt page
(`/testosterone-apexmd` → `/testosterone`, `/weight-loss` → `/glp-1-program`,
and so on), so those keep their inbound links and search ranking. The rest
have no destination yet.

Two ways forward, and they can be combined:

1. **Build the missing pages.** The nav and footer already link all of them,
   so each one that lands removes a 404.
2. **Fall back to WordPress for anything not yet rebuilt.** Give the existing
   host a second hostname (say `legacy.apexmd.com`, pointing at
   `107.180.96.144`), then add a catch-all rewrite to `vercel.json` so an
   unbuilt path is served from WordPress instead of 404ing. This lets you cut
   over the root domain now and migrate page by page.

## CTA routing — done, with two guesses to check

Every CTA now goes to the real intake form. The category vocabulary was read
off the live site by crawling all 68 sitemap URLs on 2026-09-09; the only
categories that exist are `weight-loss`, `trt`, `bloodwork`, `hrt` and
`microdosing`.

| Page | Sends to | |
|---|---|---|
| Testosterone | `form.apexmd.com/?categoryId=trt` | confirmed |
| GLP-1 Weight Loss | `form.apexmd.com/?categoryId=weight-loss` | confirmed |
| Men's Optimal Health | `form.apexmd.com/?categoryId=bloodwork` | confirmed |
| Women's Optimal Health | `form.apexmd.com/?categoryId=bloodwork` | confirmed |
| Genetics | `form.apexmd.com/?categoryId=bloodwork` | Blake's call |
| Homepage, Apex AI | `form.apexmd.com/` | no category |

Genetics has no category of its own on the live form; `bloodwork` is the
closest fit, since it is a lab-ordered test either way.

**Open:** the Genetics page sells two SKUs — Lifestyle Genetics ($499) and
Peptide Genetics ($399) — as separate buttons, and both now land on the same
link. The visitor's choice of product is lost. The live site uses
`?productid=` for exactly this (see `/peptides/` and `/microdosing/`); if
those two SKUs have productid values, the buttons should be split.

Fix any of these in one place — the `CTA` table at the top of
`_build/build.py` — then rebuild.

Patient Login goes to `ehr.apexmd.com/login` on every page.

## Also unfinished

- **7 images are still missing**, all on Men's Optimal Health (depression,
  low libido, erectile dysfunction, heart disease, belly fat, low energy,
  anxiety). They render as dashed "image needed" boxes so they cannot be
  missed. The live site has no symptom photos to borrow — see NEXT.md.
- **Copy has not cleared compliance.** The handoffs flag this themselves:
  testimonial names and case-study figures on Women's, the "300,000+ patients"
  and "4.8/5" claims on Testosterone, the "not a diagnostic test" language on
  Genetics. See `DESIGN-AUDIT.md`.
- **Pricing is inconsistent between pages** — $129 + $199/mo (TRT), $199/$399
  (Women's), $149/$399 (homepage quiz), $499/$399 (Genetics). Reconcile before
  launch, not after.
- **No analytics tag** on any page.

## Order of operations

1. Deploy to Vercel, look at the preview URL. Nothing about your live site
   changes at this step.
2. Point a subdomain (`new.apexmd.com`) at it and share that internally. The
   `.vercel.app` noindex header in `vercel.json` keeps previews out of Google;
   a custom subdomain will **not** be covered, so add a noindex there or keep
   it on the Vercel URL.
3. Decide on the WordPress fallback for the 58 unbuilt URLs, and check
   the two guessed CTA categories above.
4. **Lower the TTL on the apexmd.com A record to 300s at least 24h before
   cutting over.** This is what makes the rollback fast.
5. Change the A record. Watch for the Vercel certificate to issue — a few
   minutes, and HTTPS is broken until it does.
6. Leave the WordPress host running and paid for at least a month. Rollback is
   just pointing the A record back.

## Rollback

Set the A record back to `107.180.96.144`. With a 300s TTL you are back inside
five minutes. This is the entire reason for step 4.
