"""Build and render a mixed PDF for local integration and visual checks."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cv2
from tests.test_package import fixture_pdf
from app.package import import_pdf,export_package
from app.recovery import decode_url
from app.vision import sample

root=Path(__file__).resolve().parents[1]/'artifacts'
root.mkdir(exist_ok=True)
raw=fixture_pdf();(root/'package-sample.pdf').write_bytes(raw)
out=export_package([{'page':0,'image':None},{'page':1,'image':0},{'page':2,'image':None}],raw,[sample('clear')],{'test':'mixed native and scan export'})
(root/'package-export.pdf').write_bytes(out)
for page in import_pdf(out)['pages']:
    cv2.imwrite(str(root/f"package-export-page-{page['number']}.png"),decode_url(page['image']))
print('Rendered the three-page mixed PDF export for visual review.')
