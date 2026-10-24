"""Reproducible camera regression + exploratory evaluation; no inferred OCR accuracy."""
import argparse
import hashlib
import html
import json
import platform
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import cv2
import numpy as np
from PIL import Image, ImageOps
from app.package import import_pdf
from app.recovery import inspect, recover, decode_url
from app.page_matches import find_matches
from app.reading import read, text_of


def load_photo(path):
    with Image.open(path) as image:
        image = ImageOps.exif_transpose(image).convert('RGB')
        image.thumbnail((1600, 1600))
        return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)


def save_image(path, image):
    if not cv2.imwrite(str(path), image):
        raise RuntimeError(f'Could not write {path}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='output/benchmark-camera')
    args = parser.parse_args()
    out = ROOT / args.output
    out.mkdir(parents=True, exist_ok=True)
    pdf = ROOT/'output/pdf/scanpilot-close-camera-10-pages.pdf'
    sources = json.loads((ROOT/'output/pdf/scanpilot-close-camera-sources.json').read_text())
    cases = []
    for page, source in zip(import_pdf(pdf.read_bytes())['pages'], sources['pages']):
        cases.append({'id': f'pdf-{page["number"]:02}', 'split': 'regression',
                      'document': source['file'].split('_')[0], 'source': source['file'],
                      'source_sha256': source['original_sha256'],
                      'observed_condition': source['observed_condition'],
                      'image': decode_url(page['image']), 'frame': True})
    for document in ['sample04', 'sample12']:
        for number in [0, 1]:
            path = ROOT/f'tmp/pdfs/close-candidates/{document}_extra_picture{number:02}.jpg'
            cases.append({'id': f'{document}-{number}', 'split': 'exploratory',
                          'document': document, 'source': path.name,
                          'source_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                          'observed_condition': 'Not annotated; inspect side-by-side',
                          'image': load_photo(path), 'frame': False})
    started = time.perf_counter()
    rows, results = [], []
    for case in cases:
        tick = time.perf_counter()
        result = inspect(case['image'], page_frame=case['frame'])
        elapsed = time.perf_counter()-tick
        # Direct OCR is a genuine raw-image baseline, not the geometrically aligned before_lines.
        baseline = read(decode_url(result['original']))
        row = {k:v for k,v in case.items() if k not in ['image', 'frame']}
        row.update(status=result['status'], geometry=result['geometry_source'],
                   issues=result['issues'], inspection_seconds=round(elapsed, 3),
                   raw_text=text_of(baseline), processed_text=result['text'],
                   raw_line_count=len(baseline), processed_line_count=len(result['lines']),
                   recovered_count=0, recovery_source=None,
                   unresolved_count=sum(r['status']=='unresolved' for r in result['regions']),
                   attempts=[], human_review='pending', cer=None)
        save_image(out/f'{case["id"]}-before.jpg', decode_url(result['original']))
        save_image(out/f'{case["id"]}-after.jpg', decode_url(result['result']))
        rows.append(row); results.append(result)
        print(f'{case["id"]}: {row["geometry"]}, {row["status"]}, {elapsed:.1f}s', flush=True)
    # Match each split separately, like separate document packages in the UI.
    pairs = []
    for split in ['regression', 'exploratory']:
        indices = [i for i,c in enumerate(cases) if c['split']==split]
        matching = find_matches([decode_url(results[i]['original']) for i in indices])
        for pair in matching['pairs']:
            a, b = indices[pair['first']], indices[pair['second']]
            pairs.append({'first': a, 'second': b, 'same_document': cases[a]['document']==cases[b]['document'], **{k:v for k,v in pair.items() if k not in ['first','second']}})
    for i, (case, row) in enumerate(zip(cases, rows)):
        if not row['unresolved_count']:
            continue
        related = [p['second'] if p['first']==i else p['first'] for p in pairs if i in [p['first'],p['second']]]
        for j in related[:2]:
            tick=time.perf_counter()
            try:
                result = recover(case['image'], cases[j]['image'], first_page_frame=case['frame'])
                row['attempts'].append({'source':cases[j]['id'], 'recovered_count':result['recovered_count'], 'seconds':round(time.perf_counter()-tick,3)})
                if result['recovered_count']:
                    row.update(recovered_count=result['recovered_count'], recovery_source=cases[j]['id'],
                               final_text=result['text'], status=result['status'],
                               unresolved_count=sum(r['status']=='unresolved' for r in result['regions']))
                    save_image(out/f'{case["id"]}-final.jpg', decode_url(result['result']))
                    break
            except ValueError as error:
                row['attempts'].append({'source':cases[j]['id'], 'error':str(error), 'seconds':round(time.perf_counter()-tick,3)})
        print(f'{case["id"]}: recovered {row["recovered_count"]}; unresolved {row["unresolved_count"]}', flush=True)
    checks = {
        'page_1_recovers_from_page_2': rows[0]['recovery_source']=='pdf-02' and rows[0]['recovered_count']>0,
        'page_1_remaining_obstruction_not_declared_resolved': rows[0]['unresolved_count']>0,
        'page_2_geometry_applied': rows[1]['geometry'] in ['text-perspective','detected-edges','estimated-edges'],
        'no_cross_document_candidate_matches': all(p['same_document'] for p in pairs),
    }
    report = {'created_utc':datetime.now(timezone.utc).isoformat(), 'python':platform.python_version(),
              'opencv':cv2.__version__, 'pdf_sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),
              'code_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ['app/vision.py','app/recovery.py','app/reading.py','app/page_matches.py']},
              'source':sources['source'], 'license':sources['license'], 'attribution':sources['attribution'],
              'limitations':'10 development regression pages + 4 exploratory photos from two other documents in the same dataset. Not an independent benchmark. No verified transcription, classification labels, or region ground truth. OCR line count and model scores are not accuracy. First inspection includes cold model startup; direct OCR baseline and matching time are excluded from inspection timing. No production code was tuned during this run.',
              'total_seconds':round(time.perf_counter()-started,2),
              'median_inspection_seconds':round(statistics.median(r['inspection_seconds'] for r in rows),2),
              'checks':checks, 'pairs':pairs, 'cases':rows}
    (out/'results.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    e=html.escape
    cards=[]
    for row in rows:
        name=row['id']; final=f'<figure><img loading="lazy" src="{name}-final.jpg"><figcaption>Recovered from {e(row["recovery_source"] or "")}</figcaption></figure>' if row['recovered_count'] else ''
        issues='; '.join(f'{i["kind"]}: {i["action"]}' for i in row['issues'])
        cards.append(f'<article><h2>{e(name)} <small>{e(row["split"])}</small></h2><p>{e(row["source"])} · {e(row["observed_condition"])}</p><p><b>{e(row["geometry"])}</b> · {row["inspection_seconds"]} s · {row["recovered_count"]} regions recovered · {row["unresolved_count"]} unresolved</p><p>{e(issues)}</p><div class="images"><figure><img loading="lazy" src="{name}-before.jpg"><figcaption>Original input</figcaption></figure><figure><img loading="lazy" src="{name}-after.jpg"><figcaption>After inspection</figcaption></figure>{final}</div><details><summary>Compare OCR text</summary><div class="texts"><pre>{e(row["raw_text"])}</pre><pre>{e(row.get("final_text",row["processed_text"]))}</pre></div></details><p>Human review: pending. Check crop completeness, straightness, legibility, and copied evidence.</p></article>')
    checks_html=''.join(f'<li>{"PASS" if value else "FAIL"} — {e(key)}</li>' for key,value in checks.items())
    document=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ScanPilot camera benchmark</title><style>body{{font:16px/1.6 system-ui;color:#18344b;background:#f6f8fc;margin:0}}main{{max-width:1200px;margin:auto;padding:24px}}article,header{{background:white;border:1px solid #dce3ed;border-radius:12px;padding:24px;margin-bottom:24px}}h1,h2{{line-height:1.2}}small{{font-size:14px;color:#52687b}}.images,.texts{{display:flex;gap:16px}}figure{{margin:0;flex:1;min-width:0}}img{{width:100%;height:520px;object-fit:contain;background:#edf1f5}}pre{{flex:1;min-width:0;white-space:pre-wrap;overflow-wrap:anywhere;font:13px/1.6 monospace}}summary{{cursor:pointer;padding:16px 0}}@media(max-width:700px){{.images,.texts{{display:block}}img{{height:auto;max-height:700px}}figure{{margin-bottom:16px}}main{{padding:12px}}}}</style><main><header><h1>ScanPilot · camera evaluation</h1><p>14 real-camera cases: 10 regression pages + 4 exploratory photos.</p><p>Median inspection: {report['median_inspection_seconds']} s. End-to-end script: {report['total_seconds']} s.</p><ul>{checks_html}</ul><p>{e(report['limitations'])}</p><p>Source: <a href="{e(report['source'])}">SmartDoc 2017</a> · <a href="{e(report['license'])}">CC BY-SA 4.0</a>. {e(report['attribution'])}. Changes: EXIF orientation, resizing, and ScanPilot processing shown separately.</p></header>{''.join(cards)}</main></html>'''
    (out/'index.html').write_text(document,encoding='utf-8')
    (out/'review-template.json').write_text(json.dumps([{'id':r['id'],'correct_issue_labels':[], 'crop_preserves_content':None,'straightness_improved':None,'readability_improved':None,'recovered_text_matches_source':None,'verified_transcription':None,'notes':''} for r in rows],indent=2),encoding='utf-8')
    print(json.dumps({'checks':checks,'output':str(out)},indent=2),flush=True)


if __name__=='__main__':
    main()
