"""Local browser smoke check via an isolated Chrome DevTools port.

Requires websocket-client in the developer environment, Chrome on port 9225,
and ScanPilot on port 8765. Never connects to a user's ordinary browser profile.
"""
import base64
import json
import time
import urllib.request
from pathlib import Path

import websocket

out = Path(__file__).resolve().parents[1] / 'artifacts'
out.mkdir(exist_ok=True)
pages = json.load(urllib.request.urlopen('http://127.0.0.1:9225/json'))
page = next(p for p in pages if p['type'] == 'page')
ws = websocket.create_connection(page['webSocketDebuggerUrl'], origin='http://localhost:9225', timeout=20)
counter = 0
errors = []


def call(method, params=None):
    global counter
    counter += 1
    ident = counter
    ws.send(json.dumps({'id': ident, 'method': method, 'params': params or {}}))
    while True:
        message = json.loads(ws.recv())
        if message.get('method') == 'Runtime.exceptionThrown':
            errors.append(message['params'])
        if message.get('id') == ident:
            if 'error' in message:
                raise RuntimeError(message['error'])
            return message.get('result', {})


def evaluate(expression):
    result = call('Runtime.evaluate', {'expression':expression, 'returnByValue':True, 'awaitPromise':True})
    if 'exceptionDetails' in result:
        raise RuntimeError(result['exceptionDetails'])
    return result.get('result', {}).get('value')


def wait(expression):
    deadline = time.monotonic()+15
    while time.monotonic()<deadline:
        if evaluate(expression):
            return
        time.sleep(.1)
    raise AssertionError('Timed out: '+expression)


def screenshot(name):
    evaluate('new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
    raw = call('Page.captureScreenshot', {'format':'png'})['data']
    (out/name).write_bytes(base64.b64decode(raw))


call('Runtime.enable')
call('Page.enable')
call('Emulation.setDeviceMetricsOverride', {'width':1440,'height':1050,'deviceScaleFactor':1,'mobile':False})
call('Page.navigate', {'url':'http://127.0.0.1:8765'})
wait("document.querySelector('#upload-main') && typeof inspect === 'function'")
screenshot('desktop-empty.png')
assert evaluate('document.documentElement.scrollWidth <= innerWidth')
assert evaluate("document.querySelectorAll('h1').length === 1")
assert evaluate("!document.querySelector('.hero').innerText.includes('?')")
# Hero upload forwards to the real file input; intercept the OS picker in this check.
evaluate("window.__picked=false;document.getElementById('file-input').addEventListener('click',e=>{e.preventDefault();window.__picked=true;},{once:true});document.getElementById('hero-upload').click()")
assert evaluate('window.__picked')
evaluate("document.getElementById('hero-example').click()")
wait("currentData !== null && !busy")
assert evaluate("document.getElementById('filename').textContent.includes('miring')")
assert evaluate("document.querySelector('.workspace').getBoundingClientRect().top < innerHeight")
for kind in ['perspective','shadow','blur']:
    evaluate(f"document.querySelector('[data-sample={kind}]').click()")
    wait(f"document.querySelector('[data-sample={kind}]').getAttribute('aria-pressed') === 'true' && !busy")
    assert evaluate("document.getElementById('error').hidden")
    if kind == 'blur':
        assert evaluate("document.getElementById('status-title').textContent === 'Satu foto lagi.'")
        assert evaluate("document.getElementById('download').hidden")
    else:
        assert evaluate("!document.getElementById('download').hidden")
    evaluate("document.getElementById('compare-range').value=25; document.getElementById('compare-range').dispatchEvent(new Event('input'))")
    assert evaluate("document.getElementById('divider').style.left === '25%'")
    evaluate("document.querySelector('#compare-control button').click()")
    assert evaluate("document.querySelector('#compare-control button').getAttribute('aria-pressed') === 'true'")
    wait("document.getElementById('after-image').complete && document.getElementById('after-image').naturalWidth>0")
    screenshot(f'desktop-{kind}.png')
evaluate("document.getElementById('preview-try').click()")
wait("document.querySelector('[data-sample=perspective]').getAttribute('aria-pressed') === 'true' && !busy")

# A clear replacement after the retake path must return to review.
evaluate("(async()=>{const blob=await (await fetch('/api/sample/clear')).blob(); await inspect(blob,'foto-ulang.jpg');})()")
assert evaluate("document.getElementById('status-title').textContent !== 'Satu foto lagi.'")
# Different view modes must expose the chosen source and maintain accessible state.
evaluate("document.querySelector('[data-view=original]').click()")
assert evaluate("document.getElementById('divider').hidden && document.getElementById('after-label').hidden && document.getElementById('after-layer').style.clipPath.includes('100%')")
evaluate("document.querySelector('[data-view=result]').click()")
assert evaluate("document.getElementById('before-label').hidden && !document.getElementById('after-label').hidden && document.getElementById('after-layer').style.clipPath === 'inset(0px)'")
evaluate("document.querySelector('[data-view=compare]').click()")
assert evaluate("!document.getElementById('divider').hidden && !document.getElementById('compare-control').hidden")
# A failed replacement must not discard the previous successful result.
assert evaluate("inspect(new Blob(['invalid'],{type:'image/jpeg'}),'broken.jpg')") is False
assert evaluate("!document.getElementById('error').hidden && document.getElementById('filename').textContent === 'foto-ulang.jpg'")
# Keyboard alternative to dragging the comparison handle.
evaluate("document.getElementById('error').hidden=true;document.getElementById('compare-range').value=50;document.getElementById('compare-range').focus()")
call('Input.dispatchKeyEvent',{'type':'keyDown','key':'ArrowRight','code':'ArrowRight','windowsVirtualKeyCode':39})
call('Input.dispatchKeyEvent',{'type':'keyUp','key':'ArrowRight','code':'ArrowRight','windowsVirtualKeyCode':39})
assert evaluate("document.getElementById('compare-range').value === '51' && document.getElementById('divider').style.left === '51%'")
call('Emulation.setDeviceMetricsOverride', {'width':390,'height':844,'deviceScaleFactor':1,'mobile':True})
call('Page.navigate', {'url':'http://127.0.0.1:8765'})
wait("document.querySelector('#upload-main') && typeof inspect === 'function'")
assert evaluate('document.documentElement.scrollWidth <= innerWidth')
screenshot('mobile-empty.png')
for width in [360,768,1024,1280]:
    call('Emulation.setDeviceMetricsOverride',{'width':width,'height':900,'deviceScaleFactor':1,'mobile':False})
    assert evaluate('document.documentElement.scrollWidth <= innerWidth'), width
call('Emulation.setDeviceMetricsOverride',{'width':390,'height':844,'deviceScaleFactor':1,'mobile':True})
evaluate("document.querySelector('[data-sample=blur]').click()")
wait("document.querySelector('[data-sample=blur]').getAttribute('aria-pressed') === 'true' && !busy")
assert evaluate('document.documentElement.scrollWidth <= innerWidth')
evaluate("document.querySelector('.inspector').scrollIntoView()")
screenshot('mobile-retake.png')
for width in [360,768,1024,1280]:
    call('Emulation.setDeviceMetricsOverride',{'width':width,'height':900,'deviceScaleFactor':1,'mobile':False})
    assert evaluate('document.documentElement.scrollWidth <= innerWidth'), width
    assert evaluate("getComputedStyle(document.querySelector('.inspector')).display !== 'none'"), width
assert not errors, errors
print('Browser checks passed: desktop/mobile, 3 samples, 3 view modes, keyboard comparison, retake/replacement, failed replacement preserves result, responsive widths 360–1440, no runtime exceptions.')
ws.close()
