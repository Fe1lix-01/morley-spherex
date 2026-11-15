const {chromium} = await import(process.env.ROI_PLAYWRIGHT_MODULE ?? 'playwright');
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
const base=process.env.ROI_WEB_URL ?? 'http://localhost:3000';
const out=process.env.ROI_BROWSER_ARTIFACTS ?? '/private/tmp/full-team-browser';await fs.mkdir(out,{recursive:true});
const browser=await chromium.launch({channel:'chrome',headless:true,args:['--disable-extensions','--disable-features=Translate','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const page=await browser.newPage({viewport:{width:1600,height:1200}});
const result={errors:[],tiles:[],http:[]};page.on('pageerror',e=>result.errors.push(e.message));
page.on('response',async r=>{if(r.url().includes('Npix')||r.url().includes('Allsky')) { await r.finished(); result.tiles.push({url:r.url(),status:r.status()}); }});
const waitFrame=async frame=>{ const end=Date.now()+45000; while(Date.now()<end){ const urls=new Set(result.tiles.filter(t=>t.status===200&&t.url.includes('SPHEREx')&&t.url.includes('/Norder0/')&&t.url.endsWith('_'+frame+'.png')).map(t=>t.url)); if(urls.size===12){await page.waitForTimeout(2000);return;} await page.waitForTimeout(250); } throw new Error('Frame '+frame+' did not finish loading all 12 base tiles'); };
try{
 for(const path of ['/','/preview','/catalog','/sky-test','/phenomena/nebulosas.jpg','/frames/sim_e1_D6.png','/frames/sim_e2_D6.png','/frames/sim_e3_D6.png','/api/sky-hips/Norder3/Allsky.jpg']){
 const r=await page.request.get(base+path);result.http.push([path,r.status()]);assert.equal(r.status(),200,path);}
 await page.goto(base+'/preview');
 await page.getByRole('button',{name:'Robot asistente Ayuda',exact:true}).click();
 await page.getByLabel('Tu pregunta').fill('¿Qué es SPHEREx?');await page.getByRole('button',{name:'Enviar',exact:true}).click();await page.waitForTimeout(1800);
 const dialog=page.getByRole('dialog',{name:'Asistente de ayuda'});assert.match(await dialog.innerText(),/SPHEREx/);
 result.chat=await dialog.innerText();await page.screenshot({path:out+'/astro.png'});await page.getByRole('button',{name:'Robot asistente Cerrar',exact:true}).last().click();
 await page.getByRole('button',{name:'Análisis Barnard',exact:true}).click();await page.getByText(/Servicio no disponible:.*ETER_BARNARD/).waitFor();
 result.barnard=await page.getByText(/Servicio no disponible:.*ETER_BARNARD/).innerText();assert.match(result.barnard,/ETER_BARNARD/);
 await page.getByRole('button',{name:'Ejecutar demostración',exact:true}).click();await page.getByText(/Falta configurar: ETER_ML/).waitFor();
 await page.screenshot({path:out+'/barnard.png'});await page.getByRole('button',{name:'Cerrar panel',exact:true}).click();
 await page.getByRole('button',{name:'Mosaico SPHEREx DR1',exact:true}).click();await page.getByRole('button',{name:'Seleccionar región',exact:true}).waitFor();
 await page.getByRole('button',{name:'SPHEREx DR1',exact:true}).click();
 await page.getByRole('slider',{name:'Canal espectral SPHEREx'}).waitFor();await waitFrame(61);
 await page.screenshot({path:out+'/spherex-default.png'});
 const channel=page.getByRole('slider',{name:'Canal espectral SPHEREx'});await channel.focus();await page.keyboard.press('ArrowRight');assert.equal(await channel.getAttribute('aria-valuenow'),'63');
 await page.getByRole('slider',{name:'Brillo del mosaico'}).focus();await page.keyboard.press('ArrowLeft');
 await page.getByRole('slider',{name:'Contraste del mosaico'}).focus();await page.keyboard.press('ArrowRight');await waitFrame(62);
 await page.screenshot({path:out+'/spherex-channel63.png'}); assert.ok(result.tiles.some(t=>/Npix\d+_61\.png/.test(t.url)&&t.status===200),'channel 62 requests frame 61'); assert.ok(result.tiles.some(t=>/Npix\d+_62\.png/.test(t.url)&&t.status===200),'channel 63 requests frame 62'); result.success=true;
}catch(e){result.failure=String(e);await page.screenshot({path:out+'/team-failure.png'});process.exitCode=1;}
finally{await fs.writeFile(out+'/team-visual.json',JSON.stringify(result,null,2));console.log(JSON.stringify(result));await browser.close();}
