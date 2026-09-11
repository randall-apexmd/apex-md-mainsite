// Targeted visual-defect detection via raw CDP. For each page at each width:
//  - covered text: text whose centre point is topped by an unrelated element
//  - distorted images: painted aspect ratio differs from the file's
//  - ghost text: near-white text on a near-white effective background
//  - fixed/sticky elements and their heights; header position at scroll 0
//  - empty interactive elements (buttons/links with no text and no image)
import { spawn } from 'node:child_process';
import { writeFileSync, mkdirSync } from 'node:fs';

const OUT = process.argv[2];
const BASE = process.argv[3] || 'http://localhost:4310';
const PAGES = (process.argv[4] || 'index,concierge,testosterone,genetics,mens-optimal-health,womens-optimal-health,glp-1-program,apex-md-ai').split(',');
const WIDTHS = [ {name:'desk', w:1440, h:900, mobile:false}, {name:'phone', w:390, h:844, mobile:true} ];
mkdirSync(OUT, { recursive: true });

const chrome = spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', [
  '--headless=new', '--remote-debugging-port=9334', '--disable-gpu', '--hide-scrollbars',
  '--no-first-run', '--no-default-browser-check', `--user-data-dir=${OUT}/profile`, 'about:blank'],
  { stdio: 'ignore' });
const sleep = ms => new Promise(r => setTimeout(r, ms));
let target;
for (let i = 0; i < 40 && !target; i++) { await sleep(250);
  try { target = (await (await fetch('http://127.0.0.1:9334/json/list')).json()).find(t => t.type === 'page'); } catch {} }
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise(r => ws.onopen = r);
let id = 0; const pending = new Map();
ws.onmessage = e => { const m = JSON.parse(e.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } };
const send = (method, params = {}) => new Promise(r => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
const evaluate = async expr => { const r = await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true });
  if (r.result?.exceptionDetails) return { error: r.result.exceptionDetails.exception?.description || 'eval error' };
  return r.result?.result?.value; };
await send('Page.enable'); await send('Runtime.enable');

const PROBE = `(async()=>{
  const s=ms=>new Promise(r=>setTimeout(r,ms));
  for(let y=0;y<document.documentElement.scrollHeight;y+=innerHeight*0.6){scrollTo(0,y);await s(120);}
  scrollTo(0,0); await s(700);
  await Promise.all([...document.images].map(i=>i.complete?0:new Promise(r=>{i.onload=i.onerror=r;setTimeout(r,3000)})));
  const label=el=>{ if(!el) return '?'; const t=(el.innerText||el.getAttribute('alt')||'').trim().replace(/\\s+/g,' ').slice(0,48);
    return el.tagName.toLowerCase()+(el.className&&typeof el.className==='string'?'.'+el.className.split(' ').filter(c=>!c.startsWith('x')).slice(0,2).join('.'):'')+(t?' "'+t+'"':''); };
  const out={covered:[],distorted:[],ghost:[],fixed:[],emptyCtas:[],header:null};
  const h=document.querySelector('header.hdr'); if(h){const r=h.getBoundingClientRect(); out.header={top:Math.round(r.top),height:Math.round(r.height)};}
  // fixed / sticky elements
  for(const el of document.querySelectorAll('body *')){ const cs=getComputedStyle(el);
    if((cs.position==='fixed'||cs.position==='sticky') && el.offsetParent!==null || cs.position==='fixed'){ const r=el.getBoundingClientRect();
      if(r.height>0 && r.width>0 && cs.display!=='none' && cs.visibility!=='hidden') out.fixed.push({el:label(el).slice(0,70),pos:cs.position,top:Math.round(r.top),h:Math.round(r.height),w:Math.round(r.width)}); } }
  // distorted images
  for(const i of document.images){ const r=i.getBoundingClientRect(); if(!i.naturalWidth||r.width<24||r.height<24) continue;
    const fit=getComputedStyle(i).objectFit; if(fit==='cover'||fit==='contain'||fit==='scale-down') continue;
    const k=(r.width/r.height)/(i.naturalWidth/i.naturalHeight); if(Math.abs(k-1)>0.08) out.distorted.push({img:(i.getAttribute('src')||'').split('/').pop().split('?')[0],shown:Math.round(r.width)+'x'+Math.round(r.height),file:i.naturalWidth+'x'+i.naturalHeight,stretch:+k.toFixed(2)}); }
  // walk the page a viewport at a time for covered + ghost text
  const texts=[...document.querySelectorAll('#main h1,#main h2,#main h3,#main h4,#main p,#main li,#main a,#main button,#main span,#main div')].filter(el=>{
    if(!el.offsetParent) return false; const own=[...el.childNodes].some(n=>n.nodeType===3&&n.nodeValue.trim().length>2); return own; });
  const bgOf=el=>{ for(let e=el;e;e=e.parentElement){ const c=getComputedStyle(e).backgroundColor; const m=c.match(/[\\d.]+/g);
    if(m&&(m.length<4||+m[3]>0.5)) return m.slice(0,3).map(Number); if(getComputedStyle(e).backgroundImage!=='none') return null; } return [255,255,255]; };
  const lum=c=>{const f=v=>{v/=255;return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4)}; return 0.2126*f(c[0])+0.7152*f(c[1])+0.0722*f(c[2]);};
  const seenCov=new Set(), seenGhost=new Set();
  const H=document.documentElement.scrollHeight;
  for(let y=0;y<H;y+=innerHeight){ scrollTo(0,y); await s(60);
    for(const el of texts){ const r=el.getBoundingClientRect(); if(r.bottom<0||r.top>innerHeight||r.width<8||r.height<6) continue;
      const cx=Math.min(innerWidth-1,Math.max(0,r.left+r.width/2)), cy=r.top+Math.min(r.height/2,12);
      if(cy<0||cy>=innerHeight) continue;
      const top=document.elementFromPoint(cx,cy);
      if(top && top!==el && !el.contains(top) && !top.contains(el) && !top.closest('header.hdr') && getComputedStyle(top).position!=='fixed' && !top.closest('[style*="position: fixed"]')){
        let fixedAnc=false; for(let e=top;e;e=e.parentElement){ if(getComputedStyle(e).position==='fixed'){fixedAnc=true;break;} }
        if(!fixedAnc){ const key=label(el); if(!seenCov.has(key)){ seenCov.add(key); out.covered.push({text:key.slice(0,80),by:label(top).slice(0,60),y:Math.round(r.top+scrollY)}); } } }
      const col=getComputedStyle(el).color.match(/[\\d.]+/g).map(Number); const bg=bgOf(el);
      if(bg && getComputedStyle(el).opacity>0.05){ const a=lum(col),b=lum(bg); const ratio=(Math.max(a,b)+0.05)/(Math.min(a,b)+0.05);
        if(ratio<1.35){ const key=label(el); if(!seenGhost.has(key)){ seenGhost.add(key); out.ghost.push({text:key.slice(0,80),color:'rgb('+col.slice(0,3).join(',')+')',bg:'rgb('+bg.join(',')+')',y:Math.round(r.top+scrollY)}); } } } }
  }
  scrollTo(0,0);
  // CTAs with no visible label
  for(const a of document.querySelectorAll('#main a, #main button')){ if(!a.offsetParent) continue; const r=a.getBoundingClientRect(); if(r.width<20||r.height<16) continue;
    const txt=(a.innerText||'').trim(); const hasImg=a.querySelector('img,svg'); if(!txt && !hasImg && !a.getAttribute('aria-label')) out.emptyCtas.push({el:label(a),href:a.getAttribute('href'),box:Math.round(r.width)+'x'+Math.round(r.height),y:Math.round(r.top+scrollY)}); }
  return out; })()`;

const report = {};
for (const W of WIDTHS) {
  await send('Emulation.setDeviceMetricsOverride', { width: W.w, height: W.h, deviceScaleFactor: 1, mobile: W.mobile });
  await send('Emulation.setTouchEmulationEnabled', { enabled: W.mobile });
  for (const p of PAGES) {
    await send('Page.navigate', { url: `${BASE}/${p}.html?insp=${Date.now()}` });
    await sleep(2200);
    report[`${p}@${W.name}`] = await evaluate(PROBE);
    // one true viewport shot at scroll 0, for header placement
    const shot = await send('Page.captureScreenshot', { format: 'png' });
    writeFileSync(`${OUT}/${p}@${W.name}-top.png`, Buffer.from(shot.result.data, 'base64'));
    process.stdout.write(`${p}@${W.name} done\n`);
  }
}
writeFileSync(`${OUT}/inspect.json`, JSON.stringify(report, null, 2));
ws.close(); chrome.kill();
