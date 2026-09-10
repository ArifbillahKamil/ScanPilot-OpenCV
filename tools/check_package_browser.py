"""Real browser integration for PDF packages, page recovery and export."""
import base64
import io
import json
import time
import urllib.request
from pathlib import Path
import websocket
from pypdf import PdfReader

root=Path(__file__).resolve().parents[1]
pages=json.load(urllib.request.urlopen('http://127.0.0.1:9225/json'))
page=next(p for p in pages if p['type']=='page')
ws=websocket.create_connection(page['webSocketDebuggerUrl'],origin='http://localhost:9225',timeout=180)
counter=0;errors=[]
def call(method,params=None):
    global counter
    counter+=1;ws.send(json.dumps({'id':counter,'method':method,'params':params or {}}))
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
    end=time.monotonic()+150
    while time.monotonic()<end:
        if js('Boolean('+expression+')'):return
        time.sleep(.25)
    raise AssertionError((expression,js("$('package-error').textContent")))
def shot(name):
    js("await document.fonts.ready.then(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))))")
    (root/'artifacts'/name).write_bytes(base64.b64decode(call('Page.captureScreenshot',{'format':'png'})['data']))
def upload(path):
    doc=call('DOM.getDocument')['root']['nodeId']
    node=call('DOM.querySelector',{'nodeId':doc,'selector':'#package-input'})['nodeId']
    call('DOM.setFileInputFiles',{'nodeId':node,'files':[str(path)]})

call('Runtime.enable');call('Page.enable');call('DOM.enable')
call('Emulation.setDeviceMetricsOverride',{'width':1440,'height':1080,'deviceScaleFactor':1,'mobile':False})
call('Page.navigate',{'url':'http://127.0.0.1:8765'})
wait("document.querySelector('#package-input')")
js("setLanguage('en');$('package-workspace').scrollIntoView({block:'start'})")
assert js("document.body.classList.contains('package-mode')")
shot('package-empty-desktop.png')
upload(root/'artifacts/package-sample.pdf')
wait('packagePages.length===3 && !packageWorking && !busy')
assert js("packagePages[0].digital && packagePages[0].useResult===false")
assert js("packagePages[1].data && packagePages[2].data")
assert js("packageState(packagePages[2])==='retake'")
js("$('package-workspace').scrollIntoView({block:'start'})")
shot('package-triage-desktop.png')
js("packageOpen(packagePages[0])")
assert js("$('package-native-preview').open && $('package-native-text').textContent.includes('DIGITAL ORIGINAL')")
js("$('package-native-close').click();packageOpen(packagePages[2])")
assert js("packageActive.number===3 && firstPhoto===packagePages[2].file && window.packageWorkspace.frame")
shot('package-editor-desktop.png')
assert js("await recoverPhoto(await (await fetch('/api/sample/second?lang=en')).blob(),'second-photo.jpg',false)")
assert js("packagePages[2].data.recovered_count===1 && packagePages[2].useResult")
js("$('package-back').click()")
assert js("!packageActive && packageState(packagePages[2])==='improved'")
js("packageOpen(packagePages[1]);$('package-back').click();packageOpen(packagePages[2])")
assert js("currentData.recovered_count===1 && secondPhoto && $('second-name').textContent.includes('second-photo.jpg')")
js("$('package-back').click();window.__packageExports=[];saveBlob=(blob,name)=>window.__packageExports.push({blob,name})")
js("await packageExport()")
assert js("window.__packageExports.length===1"),js("$('package-error').textContent")
encoded=js("await window.__packageExports[0].blob.arrayBuffer().then(b=>btoa(Array.from(new Uint8Array(b),x=>String.fromCharCode(x)).join('')))")
output=base64.b64decode(encoded);(root/'artifacts/package-browser-export.pdf').write_bytes(output)
reader=PdfReader(io.BytesIO(output))
assert len(reader.pages)==3 and 'DIGITAL ORIGINAL' in reader.pages[0].extract_text()
assert 'scanpilot-review.json' in reader.attachments
for lang in ['id','en']:
    js(f"setLanguage('{lang}')")
    for width in [360,390,768,1440]:
        call('Emulation.setDeviceMetricsOverride',{'width':width,'height':900,'deviceScaleFactor':1,'mobile':width<700})
        assert js('document.documentElement.scrollWidth<=innerWidth'),(lang,width)
call('Emulation.setDeviceMetricsOverride',{'width':390,'height':900,'deviceScaleFactor':1,'mobile':True})
js("$('package-workspace').scrollIntoView({block:'start'})");shot('package-triage-mobile.png')
js("setLanguage('id')")
assert js("$('package-title').textContent.includes('Setiap halaman') && $('package-pages').textContent.includes('Halaman 3')")
js("setLanguage('en');$('package-filter').value='attention';packageRender()")
assert js("!Array.from($('package-pages').children).some(row=>row.dataset.state==='digital')")
# Switching packages keeps the existing package until a valid import completes.
js("await packageImport([new File(['invalid'],'bad.pdf',{type:'application/pdf'})])")
assert js("packagePages.length===3 && !$('package-error').hidden")
js("window.__photoRun=packageDemo();true")
wait('packageOriginal===null && packageWorking && packagePages.some(p=>!p.data)')
js("$('package-stop').click()")
wait('!packageWorking && !busy')
assert js("packagePages.some(p=>packageState(p)==='pending')")
js("await packageRun()")
assert js("packagePages.every(p=>p.data) && packagePages.length===3")
js("packageOpen(packagePages[0]);addArea([.2,.2,.2,.1]);$('package-back').click()")
assert js("packageState(packagePages[0])==='retake' && packagePages[0].manual.length===1")
js("packageOpen(packagePages[0])")
assert js("manualRegions.length===1")
js("$('package-back').click();window.__packageExports=[]")
js("await packageExport()")
assert js("window.__packageExports.length===1"),js("$('package-error').textContent")
encoded=js("await window.__packageExports[0].blob.arrayBuffer().then(b=>btoa(Array.from(new Uint8Array(b),x=>String.fromCharCode(x)).join('')))")
reader=PdfReader(io.BytesIO(base64.b64decode(encoded)))
assert len(reader.pages)==3
report=json.loads(reader.attachments['scanpilot-review.json'][0])
assert report['pages'][0]['manual_regions']==[[.2,.2,.2,.1]]
js("await packageImport(Array(21).fill(new File(['x'],'x.jpg',{type:'image/jpeg'})))")
assert js("packagePages.length===3 && $('package-error').textContent.includes('20')")
assert not errors,errors
ws.close()
print('Package browser checks passed: PDF triage, original digital page, per-page recovery and restoration, PDF export order/text/report, bilingual responsive layout, invalid import preservation.')
