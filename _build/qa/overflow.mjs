// Phone-width overflow audit: the outermost elements that run past the right
// edge and are NOT inside a horizontal scroller or an animated marquee.
import { spawn } from 'node:child_process';
const PAGES = ['index','concierge','testosterone','genetics','mens-optimal-health','womens-optimal-health','glp-1-program','apex-md-ai'];
const chrome = spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', ['--headless=new','--remote-debugging-port=9335','--disable-gpu','--hide-scrollbars','--no-first-run',`--user-data-dir=${process.argv[2]}/ovprof`,'about:blank'],{stdio:'ignore'});
const sleep=ms=>new Promise(r=>setTimeout(r,ms)); let t;
for(let i=0;i<40&&!t;i++){await sleep(250);try{t=(await (await fetch('http://127.0.0.1:9335/json/list')).json()).find(x=>x.type==='page')}catch{}}
const ws=new WebSocket(t.webSocketDebuggerUrl); await new Promise(r=>ws.onopen=r);
let id=0; const P=new Map(); ws.onmessage=e=>{const m=JSON.parse(e.data); if(m.id&&P.has(m.id)){P.get(m.id)(m);P.delete(m.id)}};
const send=(method,params={})=>new Promise(r=>{const i=++id;P.set(i,r);ws.send(JSON.stringify({id:i,method,params}))});
const ev=async x=>(await send('Runtime.evaluate',{expression:x,awaitPromise:true,returnByValue:true})).result?.result?.value;
await send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
for(const p of PAGES){
  await send('Page.navigate',{url:`http://localhost:4310/${p}.html?ov=${Date.now()}`}); await sleep(2200);
  const r=await ev(`(()=>{const vw=document.documentElement.clientWidth;
    const exempt=el=>{for(let e=el.parentElement;e&&e!==document.body;e=e.parentElement){const cs=getComputedStyle(e);
      if(/(auto|scroll)/.test(cs.overflowX))return true; if(cs.animationName&&cs.animationName!=='none')return true;} return false;};
    const over=[...document.querySelectorAll('#main *')].filter(el=>{const r=el.getBoundingClientRect(),cs=getComputedStyle(el);
      return r.width>0&&r.height>0&&r.right>vw+2&&cs.position!=='fixed'&&cs.visibility!=='hidden'&&!(cs.animationName&&cs.animationName!=='none')&&!exempt(el);});
    const outer=over.filter(el=>!over.includes(el.parentElement));
    const d=el=>{const cs=getComputedStyle(el),pc=el.parentElement?getComputedStyle(el.parentElement):{};
      return {tag:el.tagName.toLowerCase(),right:Math.round(el.getBoundingClientRect().right),w:Math.round(el.getBoundingClientRect().width),
        y:Math.round(el.getBoundingClientRect().top+scrollY),disp:cs.display,width:cs.width,minW:cs.minWidth,flex:cs.flex,ws:cs.whiteSpace,
        parent:(pc.display||'')+(pc.flexWrap&&pc.display&&pc.display.includes('flex')?'/'+pc.flexWrap+'/'+pc.flexDirection:'')+(pc.gridTemplateColumns&&pc.display==='grid'?' cols='+pc.gridTemplateColumns:''),
        kids:el.parentElement?el.parentElement.children.length:0,
        text:(el.innerText||el.getAttribute('alt')||'').trim().replace(/\\s+/g,' ').slice(0,50)};};
    return outer.slice(0,14).map(d);})()`);
  console.log('\n=== '+p+' ('+r.length+' outermost overflowing)');
  for(const x of r) console.log('  y='+x.y+' <'+x.tag+'> right='+x.right+' w='+x.w+' disp='+x.disp+' width='+x.width+' minW='+x.minW+' flex='+x.flex+' ws='+x.ws+' | parent '+x.parent+' ('+x.kids+' kids) | "'+x.text+'"');
}
ws.close(); chrome.kill();
