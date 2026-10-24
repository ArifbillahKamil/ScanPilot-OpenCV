"""Verify the generated local report in the isolated Chrome test session."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
helpers=(ROOT/'tools/check_package_browser.py').read_text().split("call('Runtime.enable');call('Page.enable');call('DOM.enable')")[0]
exec(compile(helpers,'browser_helpers','exec'))
call('Page.enable');call('Runtime.enable')
call('Page.navigate',{'url':(ROOT/'output/benchmark-camera/index.html').as_uri()})
wait("document.querySelectorAll('article').length===14")
for width in [390,1440]:
    call('Emulation.setDeviceMetricsOverride',{'width':width,'height':1000,'deviceScaleFactor':1,'mobile':width<700})
    assert js('document.documentElement.scrollWidth<=innerWidth')
    assert js("Array.from(document.images).filter(i=>i.complete).every(i=>i.naturalWidth>0)")
    shot(f'camera-benchmark-{width}.png')
assert not errors,errors
ws.close()
print('Report verified: 14 cases, local image loading, desktop/mobile layout, no JavaScript exceptions.')
