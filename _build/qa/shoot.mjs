// Full-page screenshots via raw CDP (Node's global WebSocket). No npm deps.
// Scrolls each page top-to-bottom first so scroll-reveal and lazy images fire,
// then captures beyond the viewport. Also records per-page layout diagnostics.
import { spawn } from 'node:child_process';
import { writeFileSync, mkdirSync } from 'node:fs';

const OUT = process.argv[2];
const BASE = 'http://localhost:4310';
const PAGES = ['index','concierge','testosterone','genetics','mens-optimal-health',
               'womens-optimal-health','glp-1-program','apex-md-ai','404'];
const WIDTHS = [ {name:'desk', w:1440, h:900, mobile:false},
                 {name:'phone', w:390, h:844, mobile:true} ];
mkdirSync(OUT, { recursive: true });

const chrome = spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', [
  '--headless=new', '--remote-debugging-port=9333', '--disable-gpu',
  '--hide-scrollbars', '--no-first-run', '--no-default-browser-check',
  `--user-data-dir=${OUT}/profile`, 'about:blank'], { stdio: 'ignore' });

const sleep = ms => new Promise(r => setTimeout(r, ms));
let target;
for (let i = 0; i < 40 && !target; i++) {
  await sleep(250);
  try {
    const list = await (await fetch('http://127.0.0.1:9333/json/list')).json();
    target = list.find(t => t.type === 'page');
  } catch {}
}
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise(r => ws.onopen = r);
let id = 0; const pending = new Map();
ws.onmessage = e => { const m = JSON.parse(e.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } };
const send = (method, params = {}) => new Promise(r => {
  const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
const evaluate = async expr => (await send('Runtime.evaluate',
  { expression: expr, awaitPromise: true, returnByValue: true })).result?.result?.value;

await send('Page.enable'); await send('Runtime.enable');
const report = {};

for (const W of WIDTHS) {
  await send('Emulation.setDeviceMetricsOverride',
    { width: W.w, height: W.h, deviceScaleFactor: 1, mobile: W.mobile });
  await send('Emulation.setTouchEmulationEnabled', { enabled: W.mobile });
  for (const p of PAGES) {
    await send('Page.navigate', { url: `${BASE}/${p}.html?shot=${Date.now()}` });
    await sleep(2500);
    // walk the page so IntersectionObserver reveals and lazy images fire
    await evaluate(`(async()=>{const s=ms=>new Promise(r=>setTimeout(r,ms));
      for(let y=0;y<document.documentElement.scrollHeight;y+=innerHeight*0.6){scrollTo(0,y);await s(160);}
      scrollTo(0,0);await s(900);
      await Promise.all([...document.images].map(i=>i.complete?0:new Promise(r=>{i.onload=i.onerror=r;setTimeout(r,4000)})));
      await s(400);})()`);
    const diag = await evaluate(`(()=>{
      const vw=document.documentElement.clientWidth;
      const over=[...document.querySelectorAll('body *')].filter(el=>{
        const r=el.getBoundingClientRect(); const cs=getComputedStyle(el);
        return r.width>0 && r.right>vw+2 && cs.position!=='fixed' && cs.visibility!=='hidden';
      }).slice(0,8).map(el=>(el.tagName+'.'+(el.className||'').toString().split(' ')[0]).slice(0,40)+' r='+Math.round(el.getBoundingClientRect().right));
      const hidden=[...document.querySelectorAll('#main section')].filter(s=>getComputedStyle(s).opacity==='0').length;
      const broken=[...document.images].filter(i=>i.complete&&i.naturalWidth===0).map(i=>i.getAttribute('src'));
      const tiny=[...document.querySelectorAll('#main p, #main li, #main a, #main span')].filter(el=>{
        const fs=parseFloat(getComputedStyle(el).fontSize); return el.textContent.trim().length>20 && fs<12 && el.offsetParent;}).length;
      const todo=document.querySelectorAll('.img-todo').length;
      return {scrollW:document.documentElement.scrollWidth, vw, height:document.documentElement.scrollHeight,
              horizOverflow:document.documentElement.scrollWidth>vw+1, overflowing:over, hiddenSections:hidden,
              brokenImgs:broken, tinyTextEls:tiny, todoBoxes:todo};})()`);
    report[`${p}@${W.name}`] = diag;
    const height = Math.min(diag.height, 16000);
    const shot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true,
      clip: { x: 0, y: 0, width: W.w, height, scale: 1 } });
    writeFileSync(`${OUT}/${p}@${W.name}.png`, Buffer.from(shot.result.data, 'base64'));
    process.stdout.write(`${p}@${W.name} ${height}px\n`);
  }
}
writeFileSync(`${OUT}/report.json`, JSON.stringify(report, null, 2));
ws.close(); chrome.kill();
