/*
 * Lead delivery for the apexmd.com site.
 *
 * Every form on the site (the member-guide email capture on all 12 pages, and
 * the full contact form) POSTs JSON here. This function emails the lead to the
 * team via Resend.
 *
 * WHY A FUNCTION RATHER THAN A FORM SERVICE
 * Leads stay first-party: they hit our own endpoint on our own domain and are
 * never stored by a third party. That matters here because the contact form has
 * a free-text comment box and people describe health concerns in it.
 *
 * REQUIRED ENV VARS (Vercel > Project > Settings > Environment Variables)
 *   RESEND_API_KEY   re_...   from resend.com/api-keys
 * OPTIONAL
 *   LEAD_TO          default info@apexmd.com  (comma-separated for several)
 *   LEAD_FROM        default "Apex MD Website <noreply@contact.apexmd.com>"
 *                    contact.apexmd.com is the domain verified in Resend
 *                    (2026-09-18): DKIM at resend._domainkey.contact, SPF and
 *                    return-path MX at send.contact. It is a subdomain on
 *                    purpose — the root apexmd.com carries Google Workspace MX
 *                    and SPF, which Resend's records must never touch.
 *
 * If RESEND_API_KEY is missing the function still returns 200 and logs the lead
 * to the Vercel function log, so a misconfiguration never shows the visitor an
 * error or loses the capture silently to the browser console.
 */

const RESEND_ENDPOINT = 'https://api.resend.com/emails';
const MAX_BODY = 16 * 1024;

const FIELD_LABELS = {
  first: 'First name',
  last: 'Last name',
  name: 'Name',
  business: 'Business entity',
  email: 'Email',
  phone: 'Phone',
  comment: 'Comment',
  kind: 'Form',
  page: 'Submitted from',
  offer_code: 'Offer code',
  partner: 'Partner'
};

const ATTR_LABELS = {
  first_seen: 'First seen',
  landing_page: 'Landing page',
  referrer: 'Referrer',
  session_id: 'Session',
  utm_source: 'utm_source',
  utm_medium: 'utm_medium',
  utm_campaign: 'utm_campaign',
  utm_content: 'utm_content',
  utm_term: 'utm_term',
  gclid: 'gclid',
  fbclid: 'fbclid',
  ttclid: 'ttclid',
  msclkid: 'msclkid'
};

function esc(v) {
  return String(v == null ? '' : v)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function validEmail(v) {
  return typeof v === 'string' && /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v.trim()) && v.length < 254;
}

function rows(obj, labels) {
  return Object.keys(labels)
    .filter(function (k) { return obj[k] !== undefined && obj[k] !== null && String(obj[k]).trim() !== ''; })
    .map(function (k) {
      return '<tr>' +
        '<td style="padding:6px 14px 6px 0;color:#595959;font:13px system-ui,sans-serif;white-space:nowrap;vertical-align:top">' + esc(labels[k]) + '</td>' +
        '<td style="padding:6px 0;color:#101010;font:13px system-ui,sans-serif">' + esc(obj[k]).replace(/\n/g, '<br>') + '</td>' +
      '</tr>';
    }).join('');
}

async function readJson(req) {
  if (req.body && typeof req.body === 'object') return req.body;
  const chunks = [];
  let size = 0;
  for await (const c of req) {
    size += c.length;
    if (size > MAX_BODY) throw new Error('payload too large');
    chunks.push(c);
  }
  const raw = Buffer.concat(chunks).toString('utf8');
  return raw ? JSON.parse(raw) : {};
}

module.exports = async function handler(req, res) {
  res.setHeader('Cache-Control', 'no-store, max-age=0');

  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return res.status(405).json({ ok: false, error: 'method-not-allowed' });
  }

  const debug = /[?&]debug=1(&|$)/.test(req.url || '');

  let body;
  try {
    body = await readJson(req);
  } catch (err) {
    return res.status(400).json({ ok: false, error: 'bad-request' });
  }

  // Honeypot: a field no human sees. Bots fill everything, so a value here is
  // a bot. Answer 200 so it believes it succeeded and does not retry.
  if (body.company) {
    console.log(JSON.stringify({ event: 'lead_rejected', reason: 'honeypot' }));
    return res.status(200).json({ ok: true });
  }

  if (!validEmail(body.email)) {
    return res.status(400).json({ ok: false, error: 'invalid-email' });
  }

  const kind = ['contact', 'partner'].indexOf(body.kind) >= 0 ? body.kind : 'lead';
  const name = (body.name || [body.first, body.last].filter(Boolean).join(' ')).trim();
  const who = name ? ' — ' + name : '';
  const subject = kind === 'contact'
    ? 'Apex MD site — contact form' + who
    : kind === 'partner'
      ? 'Apex MD site — PARTNER application' +
        (body.business ? ' — ' + body.business : who)
      : 'Apex MD site — enquiry';

  const attrRows = rows(body, ATTR_LABELS);
  const html =
    '<div style="max-width:640px;margin:0 auto;font:14px system-ui,sans-serif;color:#101010">' +
      '<p style="margin:0 0 4px;font:700 11px system-ui;letter-spacing:.14em;text-transform:uppercase;color:#d30704">Apex MD</p>' +
      '<h2 style="margin:0 0 18px;font-size:20px">' + esc(subject) + '</h2>' +
      '<table style="border-collapse:collapse;width:100%">' + rows(body, FIELD_LABELS) + '</table>' +
      (attrRows
        ? '<p style="margin:22px 0 6px;font:700 11px system-ui;letter-spacing:.12em;text-transform:uppercase;color:#8C8C8C">Attribution</p>' +
          '<table style="border-collapse:collapse;width:100%">' + attrRows + '</table>'
        : '') +
      '<p style="margin:22px 0 0;font-size:12px;color:#8C8C8C">Reply directly to this email to reach the person who submitted it.</p>' +
    '</div>';

  const to = (process.env.LEAD_TO || 'info@apexmd.com').split(',').map(function (s) { return s.trim(); }).filter(Boolean);
  const from = process.env.LEAD_FROM || 'Apex MD Website <noreply@contact.apexmd.com>';

  if (!process.env.RESEND_API_KEY) {
    // Never fail in front of the visitor over a missing key. The lead is in the
    // Vercel log and can be recovered.
    console.log(JSON.stringify({ event: 'lead_unsent', reason: 'no-resend-key', kind: kind, lead: body }));
    return res.status(200).json({ ok: true, delivered: false, why: debug ? 'no-resend-key' : undefined });
  }

  let delivered = false;
  let detail = '';
  let resendId = '';
  try {
    const controller = new AbortController();
    const timer = setTimeout(function () { controller.abort(); }, 8000);
    const r = await fetch(RESEND_ENDPOINT, {
      method: 'POST',
      signal: controller.signal,
      headers: {
        'Authorization': 'Bearer ' + process.env.RESEND_API_KEY,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        from: from,
        to: to,
        // so the team can just hit reply and land in the visitor's inbox
        reply_to: body.email,
        subject: subject,
        html: html
      })
    });
    clearTimeout(timer);
    delivered = r.ok;
    const text = await r.text();
    if (r.ok) {
      try { resendId = JSON.parse(text).id || ''; } catch (e) {}
    } else {
      detail = 'resend-' + r.status + ' ' + text.slice(0, 300);
    }
  } catch (err) {
    detail = 'error:' + (err && err.name ? err.name : 'unknown');
  }

  // Always log the lead itself: if Resend is down or misconfigured the capture
  // is still recoverable from the Vercel dashboard rather than lost.
  console.log(JSON.stringify({
    event: 'lead', kind: kind, delivered: delivered, detail: detail, resend_id: resendId,
    email: body.email, page: body.page, lead: delivered ? undefined : body
  }));

  // 200 either way: the visitor did their part, and a delivery problem on our
  // side should not read to them as their submission failing.
  // ?debug=1 also names the sender, the recipients and Resend's message id,
  // so "it said delivered but I don't see it" can be traced in Resend's logs.
  // Addresses only — never the key.
  return res.status(200).json(debug
    ? { ok: true, delivered: delivered, why: detail || undefined,
        from: from, to: to, resend_id: resendId || undefined }
    : { ok: true, delivered: delivered });
};
