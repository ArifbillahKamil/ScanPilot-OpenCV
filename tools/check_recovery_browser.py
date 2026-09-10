"""Real UI -> API -> OCR -> recovery -> exports, via isolated Chrome CDP."""
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
        message=json.loads(ws.recv())
        if message.get('method')=='Runtime.exceptionThrown': errors.append(message['params'])
        if message.get('id')==counter:
            if 'error' in message: raise RuntimeError(message['error'])
            return message.get('result',{})


def js(expression):
    if 'await ' in expression:
        expression='(async()=>('+expression+'))()'
    result=call('Runtime.evaluate',{'expression':expression,'returnByValue':True,'awaitPromise':True})
    if 'exceptionDetails' in result: raise RuntimeError(result['exceptionDetails'])
    return result.get('result',{}).get('value')


def wait(expression):
    deadline=time.monotonic()+45
    while time.monotonic()<deadline:
        if js('Boolean('+expression+')'): return
        time.sleep(.15)
    raise AssertionError('Timed out: '+expression)


def shot(name):
    raw=call('Page.captureScreenshot',{'format':'png'})['data']
    (root/'artifacts'/name).write_bytes(base64.b64decode(raw))


call('Runtime.enable');call('Page.enable')
call('Page.addScriptToEvaluateOnNewDocument',{'source':"localStorage.setItem('scanpilot-language','id')"})
call('Emulation.setDeviceMetricsOverride',{'width':1440,'height':1050,'deviceScaleFactor':1,'mobile':False})
call('Page.navigate',{'url':'http://127.0.0.1:8765'})
wait("typeof recoverPhoto==='function' && document.querySelector('[data-sample=covered]')")
js("document.querySelector('[data-sample=covered]').click()")
wait("currentData && !busy")
assert js("currentData.status==='retake' && !currentData.text.includes('271.000')")
assert js("!$('continue-recovery').hidden && !$('demo-recovery').hidden")
js("$('continue-recovery').click()")
shot('recovery-before-desktop.png')
js("$('demo-recovery').click()")
wait("currentData.second_aligned && !busy")
assert js("currentData.recovered_count===1 && currentData.lines.some(l=>l.text.includes('271.000')&&l.source==='photo-2')")
assert js("$('evidence-overlay').querySelectorAll('rect[data-status=recovered]').length===1")
js("$('reading-view').value='first';$('reading-view').dispatchEvent(new Event('change'))")
assert js("!$('ocr-lines').textContent.includes('271.000')")
js("$('reading-view').value='result';$('reading-view').dispatchEvent(new Event('change'))")
assert js("$('ocr-lines').textContent.includes('271.000')")
js("Array.from(document.querySelectorAll('.ocr-line')).find(b=>b.textContent.includes('271.000')).click()")
wait("$('source-two').width>100")
assert js("!$('source-inspect').hidden && $('source-title').textContent==='Foto 2'")
js("$('recovery').scrollIntoView({block:'start'})")
shot('recovery-after-desktop.png')
assert js("!await recoverPhoto(new Blob(['bad image']),'bad.jpg')")
assert js("currentData.recovered_count===1 && $('error').textContent.includes('tetap ditampilkan')")
js("$('error').hidden=true;window.__exports=[];saveBlob=(blob,name)=>{window.__exports.push({blob,name});};$('export-text').click();$('export-report').click()")
wait('window.__exports.length===2')
assert js("(await window.__exports.find(x=>x.name.endsWith('.txt')).blob.text()).includes('271.000')")
assert js("JSON.parse(await window.__exports.find(x=>x.name.endsWith('.json')).blob.text()).sources.every(s=>s.sha256.length===64)")
js("$('export-pdf').click()")
wait('!busy && window.__exports.length===3')
assert js("(await window.__exports.find(x=>x.name.endsWith('.pdf')).blob.text()).startsWith('%PDF')")
js("$('add-coordinates').click()")
assert js("manualRegions.length===1 && document.querySelector('[data-status=selected]')!==null")
js("Array.from(document.querySelectorAll('.region-item')).find(b=>b.textContent.includes('Hapus')).click()")
assert js('manualRegions.length===0')
for width in [360,390,680,768,1024,1440]:
    call('Emulation.setDeviceMetricsOverride',{'width':width,'height':844,'deviceScaleFactor':1,'mobile':width<700})
    assert js('document.documentElement.scrollWidth<=innerWidth'),width
call('Emulation.setDeviceMetricsOverride',{'width':390,'height':844,'deviceScaleFactor':1,'mobile':True})
js("$('recovery').scrollIntoView({block:'start'})")
shot('recovery-mobile.png')
js("$('source-inspect').scrollIntoView({block:'start'})")
shot('recovery-source-mobile.png')
assert not errors,errors
ws.close()
print('Recovery browser checks passed: real two-photo OCR, source crops, invalid replacement, TXT/JSON/PDF, manual region, 360-1440px, no runtime exceptions.')
