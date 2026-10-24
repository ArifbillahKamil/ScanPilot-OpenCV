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
call('Page.navigate',{'url':'http://127.0.0.1:8766'})
wait("document.querySelector('#package-input')")
js("setLanguage('en')")
upload(root/'output/pdf/scanpilot-close-camera-10-pages.pdf')
wait('packagePages.length===10')
# Package processing includes OCR and independent cross-view validation.
end=time.monotonic()+480
while time.monotonic()<end and js('packageWorking || busy'):
    print(js("$('package-progress').textContent"),flush=True)
    time.sleep(5)
assert js('!packageWorking && !busy')
print(js("JSON.stringify(packagePages.map(p=>({page:p.number,geometry:p.data?.geometry_source,recovered:p.data?.recovered_count,source:p.recoveryFrom,related:p.related?.map(q=>q.number),error:p.error,note:p.recoveryNote})))"),flush=True)
assert js('packagePages[0].recoveryFrom===2 && packagePages[0].data.recovered_count>=1')
assert js("packagePages[1].data.issues.some(i=>i.kind==='perspective'&&i.action==='Diperbaiki')")
assert js("packagePages[0].data.regions.some(r=>r.status==='unresolved')")
js("$('package-filter').value='attention';packageRender();$('package-workspace').scrollIntoView({block:'start'})")
shot('automatic-evidence-desktop.png')
js('packageOpen(packagePages[0])')
assert js("secondPhoto && $('second-name').textContent.includes('Page 2')")
js("$('recovery').scrollIntoView({block:'start'})")
shot('automatic-evidence-recovered.png')
js("$('package-back').click();setLanguage('id')")
assert js("$('package-pages').textContent.includes('Dipulihkan menggunakan halaman 2')")
assert js('packageReport().pages[0].recovered_from_page===2')
call('Emulation.setDeviceMetricsOverride',{'width':390,'height':900,'deviceScaleFactor':1,'mobile':True})
assert js('document.documentElement.scrollWidth<=innerWidth')
assert not errors,errors
ws.close()
print('Real PDF automatic evidence browser checks passed.',flush=True)