// Close-up screenshots of specific elements, optionally after a click.
//   node _build/qa/peek.mjs <outdir> '<json spec>'
// spec: [{"page":"glp-1-program","w":390,"sel":"[data-cmp]","click":"[data-pick=hims]","name":"cmp-phone-hims"}]
// Scrolls the whole page first so scroll-reveal and lazy images have fired.
import { spawn } from 'node:child_process';
import { writeFileSync, mkdirSync } from 'node:fs';

const OUT = process.argv[2];
const SPEC = JSON.parse(process.argv[3]);
mkdirSync(OUT, { recursive: true });
const chrome = spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', ['--headless=new',
  '--remote-debugging-port=9337', '--disable-gpu', '--hide-scrollbars', '--no-first-run',
  `--user-data-dir=${OUT}/profile`, 'about:blank'], { stdio: 'ignore' });
const sleep = ms => new Promise(r => setTimeout(r, ms));
let t;
for (let i = 0; i < 40 && !t; i++) { await sleep(250);
  try { t = (await (await fetch('http://127.0.0.1:9337/json/list')).json()).find(x => x.type === 'page'); } catch {} }
const ws = new WebSocket(t.webSocketDebuggerUrl); await new Promise(r => ws.onopen = r);
let id = 0; const P = new Map();
ws.onmessage = e => { const m = JSON.parse(e.data); if (m.id && P.has(m.id)) { P.get(m.id)(m); P.delete(m.id); } };
const send = (method, params = {}) => new Promise(r => { const i = ++id; P.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async x => (await send('Runtime.evaluate', { expression: x, awaitPromise: true, returnByValue: true })).result?.result?.value;
await send('Page.enable');

for (const s of SPEC) {
  await send('Emulation.setDeviceMetricsOverride', { width: s.w, height: s.w < 700 ? 844 : 900, deviceScaleFactor: 1, mobile: s.w < 700 });
  await send('Page.navigate', { url: `http://localhost:4310/${s.page}.html?peek=${Date.now()}` });
  await sleep(2000);
  const box = await ev(`(async()=>{const w=ms=>new Promise(r=>setTimeout(r,ms));
    document.documentElement.style.scrollBehavior='auto';
    for(let y=0;y<document.documentElement.scrollHeight;y+=innerHeight*0.6){scrollTo(0,y);await w(90);}
    const el=document.querySelector(${JSON.stringify(s.sel)}); if(!el) return null;
    el.scrollIntoView({block:'center'}); await w(1600);
    ${s.click ? `const c=document.querySelector(${JSON.stringify(s.click)}); if(c){c.click(); await w(500);}` : ''}
    const r=el.getBoundingClientRect(); return {x:0,y:Math.max(0,r.top+scrollY-(${s.pad ?? 30})),h:r.height+2*(${s.pad ?? 30})};})()`);
  if (!box) { console.log(`${s.name}: selector not found`); continue; }
  const shot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true,
    clip: { x: 0, y: box.y, width: s.w, height: Math.min(box.h, 4000), scale: 1 } });
  writeFileSync(`${OUT}/${s.name}.png`, Buffer.from(shot.result.data, 'base64'));
  console.log(`${s.name}: ${s.w}x${Math.round(box.h)}`);
}
ws.close(); chrome.kill();
