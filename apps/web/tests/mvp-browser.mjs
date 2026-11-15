const {chromium}=await import(process.env.ROI_PLAYWRIGHT_MODULE??'playwright');
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
const base=process.env.ROI_WEB_URL??'http://localhost:3000';
const api=process.env.ROI_API_URL??'http://127.0.0.1:8000/api/v1';
const out=process.env.ROI_BROWSER_ARTIFACTS??'/private/tmp/mvp-browser';await fs.mkdir(out,{recursive:true});
const browser=await chromium.launch({channel:'chrome',headless:true,args:['--disable-extensions','--disable-features=Translate','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const page=await browser.newPage({viewport:{width:1600,height:1200}});const report={targets:[],errors:[]};page.on('pageerror',e=>report.errors.push(e.message));
async function coordinates(testid){return JSON.parse(await page.getByTestId(testid).getAttribute('data-target'));}
try{
 const targets=await (await page.request.get(api+'/science/workflow/targets')).json();
 await page.goto(base+'/preview');
 for(const t of targets){
  await page.getByLabel('Candidato o región').selectOption(t.id);
  await page.waitForFunction(id=>JSON.parse(document.querySelector('[data-testid=eter-target]').dataset.target).id===id,t.id);
  const eter=await coordinates('eter-target');assert.equal(eter.ra,t.ra);assert.equal(eter.dec,t.dec);
  await page.getByRole('button',{name:'Iniciar ROI del objetivo',exact:true}).click();
  await page.getByTestId('mosaic-target').waitFor();const mosaic=await coordinates('mosaic-target');assert.equal(mosaic.id,t.id);assert.equal(mosaic.ra,t.ra);
  await page.getByRole('button',{name:'Seleccionar región',exact:true}).click();
  const roi=JSON.parse(await page.getByTestId('roi-coordinates').getAttribute('data-region'));assert.ok(Math.abs(roi.center.ra-t.ra)<1e-9);assert.ok(Math.abs(roi.center.dec-t.dec)<1e-9);
  await page.getByRole('button',{name:'Confirmar región',exact:true}).click();
  await page.getByRole('button',{name:'Buscar FITS locales del objetivo',exact:true}).click();await page.getByText(/Catálogo local: BLOCKED/).waitFor();
  assert.equal(await page.getByLabel('FITS local registrado').count(),0);
  await page.getByRole('button',{name:'Visor ÉTER',exact:true}).click();assert.equal((await coordinates('eter-target')).id,t.id);
  await page.getByRole('button',{name:'Mosaico SPHEREx DR1',exact:true}).click();
  await page.getByLabel('Elegir candidato',{exact:true}).click();await page.locator(`[role=option][data-value="${t.id}"]`).click();
  await page.getByRole('button',{name:'Visor ÉTER',exact:true}).click();assert.equal((await coordinates('eter-target')).id,t.id);
  report.targets.push({id:t.id,coordinates:[t.ra,t.dec],epoch:t.epoch,sync:'PASS',local_science:'BLOCKED',reason:'No local FITS coverage'});
 }
 await page.getByRole('button',{name:'Mosaico SPHEREx DR1',exact:true}).click();
 await page.getByLabel('RA (°)',{exact:true}).fill('210.8022671');await page.getByLabel('Dec (°)',{exact:true}).fill('54.34895');
 await page.getByRole('button',{name:'Aplicar centro',exact:true}).click();await page.getByRole('button',{name:'Confirmar región',exact:true}).click();
 await page.getByRole('button',{name:'Actualizar catálogo FITS local',exact:true}).click();await page.getByLabel('FITS local registrado',{exact:true}).waitFor({timeout:45000});
 const region=JSON.parse(await page.getByTestId('roi-coordinates').getAttribute('data-region'));
 const found=await (await page.request.post(api+'/science/workflow/catalog/search',{data:{region}})).json();
 const original=found.products.find(p=>JSON.stringify(p.shape)==='[102,201,201]'&&!p.derived);assert.ok(original);
 await page.getByLabel('FITS local registrado',{exact:true}).click();await page.locator(`[role=option][data-value="${original.id}"]`).click();
 await page.getByRole('button',{name:'Usar FITS registrado',exact:true}).click();await page.getByLabel('Extensión científica',{exact:true}).waitFor({timeout:30000});report.registered_fits='PASS';
 await page.locator('input[type=file]').last().setInputFiles(process.env.ROI_TEST_FITS);
 await page.getByRole('button',{name:'Seleccionar centro del FITS',exact:true}).waitFor();await page.getByRole('button',{name:'Seleccionar centro del FITS',exact:true}).click();
 await page.getByRole('button',{name:'Confirmar región',exact:true}).click();
 await page.getByRole('button',{name:'Extraer región',exact:true}).click();await page.getByText('Válidos: 3750/4489',{exact:false}).waitFor({timeout:45000});
 await page.getByRole('button',{name:'Analizar FITS y comprobar épocas',exact:true}).click();await page.getByText('Resumen científico: PASS · 102 planos',{exact:true}).waitFor({timeout:45000});
 await page.getByRole('link',{name:'Descargar análisis JSON',exact:true}).waitFor();
 const [download]=await Promise.all([page.waitForEvent('download'),page.getByRole('link',{name:'Descargar análisis JSON',exact:true}).click()]);await download.saveAs(out+'/m101-analysis.json');
 const analysis=JSON.parse(await fs.readFile(out+'/m101-analysis.json','utf8'));assert.equal(analysis.channels[0].valid_pixels,3750);assert.equal(analysis.channels.length,102);assert.equal(analysis.temporal.status,'BLOCKED');assert.equal(analysis.ml.status,'BLOCKED');
 report.m101={shape:[102,67,67],channel1:3750,analysis:'PASS',temporal:analysis.temporal.status,ml:analysis.ml.status};
 await page.screenshot({path:out+'/m101-science.png'});
 await page.getByRole('button',{name:'Visor ÉTER',exact:true}).click();await page.getByRole('button',{name:'Mosaico SPHEREx DR1',exact:true}).click();await page.getByText('Resumen científico: PASS · 102 planos',{exact:true}).waitFor();
 report.product_persisted=true;assert.deepEqual(report.errors,[]);report.success=true;
}catch(e){report.failure=String(e);await page.screenshot({path:out+'/failure.png'});process.exitCode=1;}
finally{await fs.writeFile(out+'/matrix.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report));await browser.close();}
