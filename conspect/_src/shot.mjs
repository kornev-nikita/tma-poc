import { chromium } from 'playwright';
import { resolve } from 'path';
import { existsSync, readdirSync } from 'fs';
import { homedir } from 'os';
function findChromium(){
  const c = resolve(homedir(),'Library/Caches/ms-playwright');
  if(!existsSync(c)) return undefined;
  for(const d of readdirSync(c).filter(x=>x.startsWith('chromium-')).sort().reverse())
    for(const sub of ['chrome-mac-arm64','chrome-mac']){
      const e = resolve(c,d,sub,'Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing');
      if(existsSync(e)) return e;
    }
}
const exe = findChromium();
const b = await chromium.launch(exe?{executablePath:exe}:{});
const pg = await b.newPage({ viewport:{width:390,height:844}, deviceScaleFactor:2 });
await pg.goto('file://'+resolve('/tmp/conspect-app/index.html'),{waitUntil:'networkidle'});
await pg.waitForTimeout(300);
await pg.screenshot({ path:'/tmp/conspect-app/a_top.png' });   // первый экран, весь конспект
// zoom в один из top-level узлов с детьми
const zoomed = await pg.evaluate(()=>{ const el=document.querySelector('.bullet.zoomable'); if(el){el.click(); return true;} return false; });
await pg.waitForTimeout(200);
await pg.screenshot({ path:'/tmp/conspect-app/a_zoom.png' });
console.log('shots done, zoomed:', zoomed);
await b.close();
