"""Exercise both languages against real OCR in the isolated Chrome profile."""
import base64
import json
import time
import urllib.request
from pathlib import Path
import websocket

root=Path(__file__).resolve().parents[1]
pages=json.load(urllib.request.urlopen('http://127.0.0.1:9225/json'))
page=next(p for p in pages if p['type']=='page')
ws=websocket.create_connection(page['webSocketDebuggerUrl'],origin='http://localhost:9225',timeout=60)
counter=0
errors=[]
def call(method,params=None):
    global counter
    counter+=1
    ws.send(json.dumps({'id':counter,'method':method,'params':params or {}}))
    while True:
        msg=json.loads(ws.recv())
        if msg.get('method')=='Runtime.exceptionThrown':errors.append(msg['params'])
        if msg.get('id')==counter:
            if 'error' in msg:raise RuntimeError(msg['error'])
            return msg.get('result',{})
def js(expression):
    if 'await ' in expression:expression='(async()=>('+expression+'))()'
    result=call('Runtime.evaluate',{'expression':expression,'returnByValue':True,'awaitPromise':True})
    if 'exceptionDetails' in result:raise RuntimeError(result['exceptionDetails'])
    return result.get('result',{}).get('value')
def wait(expression):
    deadline=time.monotonic()+45
    while time.monotonic()<deadline:
        if js('Boolean('+expression+')'):return
        time.sleep(.15)
    raise AssertionError(expression)
def shot(name):
    js("await document.fonts.ready.then(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))))")
    (root/'artifacts'/name).write_bytes(base64.b64decode(call('Page.captureScreenshot',{'format':'png'})['data']))

call('Runtime.enable');call('Page.enable')
call('Emulation.setDeviceMetricsOverride',{'width':1440,'height':1050,'deviceScaleFactor':1,'mobile':False})
script=call('Page.addScriptToEvaluateOnNewDocument',{'source':"localStorage.removeItem('scanpilot-language')"})['identifier']
call('Page.navigate',{'url':'http://127.0.0.1:8765'})
wait("document.querySelector('#language-select')")
js("document.body.classList.remove('package-mode')")
call('Page.removeScriptToEvaluateOnNewDocument',{'identifier':script})
assert js("language==='en' && document.documentElement.lang==='en'")
assert js("$('hero-title').textContent.includes('Documents,') && $('upload-main').textContent.includes('Choose document photo')")
shot('english-desktop.png')
js("document.querySelector('[data-sample=covered]').click()")
wait('currentData && !busy')
assert js("$('instruction').textContent.startsWith('Some regions cannot be verified')")
assert js("!$('trace').textContent.includes('Memilih')")
assert js("firstSampleLanguage==='en'")
js("window.__lines=JSON.stringify(currentData.lines);setLanguage('id')")
assert js("$('status-title').textContent==='Satu foto lagi.' && $('instruction').textContent.startsWith('Ada bagian')")
assert js('JSON.stringify(currentData.lines)===window.__lines')
js("$('demo-recovery').click()")
wait('currentData.second_aligned && !busy')
assert js("currentData.recovered_count===1 && firstSampleLanguage==='en'")
assert js("currentData.lines.some(l=>l.text.includes('271.000')&&l.source==='photo-2')")
assert js("!$('recovered-preview').hidden && $('recovered-preview-lines').textContent.includes('271.000')")
assert js("!$('review-recovered').hidden && !$('download-reviewed').hidden && !$('add-photo').classList.contains('primary')")
js("setLanguage('en');$('recovery').scrollIntoView({block:'start'})")
assert js("$('recovery-summary').textContent.startsWith('1 region recovered.') && $('recovery-summary').textContent.includes('marked regions')")
shot('polished-recovery-desktop.png')
call('Emulation.setDeviceMetricsOverride',{'width':390,'height':844,'deviceScaleFactor':1,'mobile':True})
js("$('recovery').scrollIntoView({block:'start'})")
assert js("document.documentElement.scrollWidth<=innerWidth")
shot('polished-recovery-mobile.png')
js("$('mobile-review-recovered').click()")
assert js("document.activeElement.classList.contains('recovered-excerpt')")
shot('polished-recovered-text-mobile.png')
js("$('review-recovered').focus();$('review-recovered').click()")
assert js("!$('source-inspect').hidden && document.activeElement.id==='close-source'")
js("$('close-source').click()")
assert js("document.activeElement.id==='review-recovered'")
js("setLanguage('id')")
call('Emulation.setDeviceMetricsOverride',{'width':1440,'height':1050,'deviceScaleFactor':1,'mobile':False})
js("$('add-coordinates').click();currentView='result';updateComparison();window.__regions=JSON.stringify(manualRegions);window.__lines=JSON.stringify(currentData.lines);setLanguage('en')")
assert js("currentView==='result' && JSON.stringify(manualRegions)===window.__regions && JSON.stringify(currentData.lines)===window.__lines")
assert js("$('region-list').textContent.includes('Remove selection')")
js("Array.from(document.querySelectorAll('.ocr-line')).find(b=>b.textContent.includes('271.000')).click()")
assert js("$('source-title').textContent==='Photo 2' && $('source-note').textContent.startsWith('OCR reading:')")
js("setLanguage('id')")
assert js("!$('source-inspect').hidden && $('source-title').textContent==='Foto 2' && $('source-note').textContent.startsWith('Bacaan OCR:')")
assert js("reviewText().startsWith('SCANPILOT / HASIL OCR UNTUK DITINJAU')")
js("setLanguage('en')")
assert js("reviewText().startsWith('SCANPILOT / OCR RESULT FOR REVIEW')")
assert js("!await recoverPhoto(new Blob(['bad bytes']),'Periksa')")
assert js("$('error').textContent.includes('supported image') && $('error').textContent.includes('previous document result')")
js("setLanguage('id')")
assert js("$('error').textContent.includes('File tidak dapat dibaca') && $('error').textContent.includes('tetap ditampilkan')")
js("setLanguage('en');window.__exports=[];saveBlob=(blob,name)=>window.__exports.push({blob,name});$('export-report').click();$('export-text').click();$('download-reviewed').click()")
wait('window.__exports.length===3 && !busy')
assert js("JSON.parse(await window.__exports.find(x=>x.name.endsWith('.json')).blob.text()).language==='en'")
assert js("JSON.parse(await window.__exports.find(x=>x.name.endsWith('.json')).blob.text()).trace.every(x=>!x.title.includes('Membaca'))")
assert js("(await window.__exports.find(x=>x.name.endsWith('.txt')).blob.text()).includes('271.000')")
for lang in ['id','en']:
    js(f"setLanguage('{lang}')")
    for width in [360,390,768,1024,1440]:
        call('Emulation.setDeviceMetricsOverride',{'width':width,'height':844,'deviceScaleFactor':1,'mobile':width<700})
        assert js('document.documentElement.scrollWidth<=innerWidth'),(lang,width)
call('Emulation.setDeviceMetricsOverride',{'width':390,'height':844,'deviceScaleFactor':1,'mobile':True})
js("window.scrollTo(0,0)")
shot('english-mobile.png')
js("$('recovery').scrollIntoView({block:'start'})")
shot('english-recovery-mobile.png')
# A selected language survives reload; documents intentionally do not.
js("setLanguage('id')")
call('Page.reload')
wait("document.querySelector('#language-select') && document.documentElement.lang==='id'")
assert js("$('upload-main').textContent.includes('Pilih foto dokumen')")
# User filenames are not UI copy, even when identical to a translation key.
assert js("await inspect(await (await fetch('/api/sample/clear?lang=id')).blob(),'Periksa',false)")
js("setLanguage('en')")
assert js("$('filename').textContent==='Periksa'")
assert js("await inspect(await (await fetch('/api/sample/perspective?lang=en')).blob(),'Perspective',true)")
assert js("$('diagnosis-list').textContent.includes('Tilted page') && $('diagnosis-list').textContent.includes('Perspective distortion')")
js("setLanguage('id')")
assert js("$('diagnosis-title').textContent==='Diagnosis otomatis' && $('diagnosis-list').textContent.includes('Halaman miring')")
js("setLanguage('en');$('diagnosis').scrollIntoView({block:'center'})")
shot('diagnosis-mobile.png')
assert not errors,errors
ws.close()
print('Bilingual browser checks passed: default English, persistence, both languages, live switching without data loss, real two-photo OCR, error messages, source views, exports, filenames, and 360-1440px layouts.')
