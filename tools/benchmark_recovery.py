"""Synthetic ablation only: not a real-photo accuracy benchmark."""
import json
from pathlib import Path
import re
import statistics
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.vision import sample, analyze
from app.recovery import inspect, recover, decode_url
from app.reading import read, text_of


def amount_read(text):
    match=re.search(r'Rp\s*([0-9., ]+)',text)
    return re.sub(r'\D','',match.group(1)) if match else ''


def main():
    # New amounts/identifiers exercise the actual OCR rather than a known demo answer.
    cases=[('184.500','BENCH-101'),('326.750','BENCH-102'),('592.000','BENCH-103'),
           ('718.250','BENCH-104'),('963.400','BENCH-105')]
    rows=[]
    read(sample('clear'))  # Warm-up excluded from measured two-photo latency.
    for amount,identifier in cases:
        first=sample('covered',amount,identifier)
        second=sample('second',amount,identifier)
        baseline=amount_read(text_of(read(first)))
        fixed=amount_read(text_of(read(decode_url(analyze(first)['result']))))
        started=time.perf_counter()
        recovered=recover(first,second)
        elapsed=round((time.perf_counter()-started)*1000)
        actual=amount_read(recovered['text'])
        expected=amount.replace('.','')
        row={'id':identifier,'expected_amount':expected,'raw_ocr':baseline,'fixed_pipeline':fixed,
             'two_photo':actual,'exact_match':actual==expected,'recovered_areas':recovered['recovered_count'],
             'elapsed_ms':elapsed,'registration':recovered['registration']}
        rows.append(row)
        print(json.dumps(row),flush=True)
    report={'dataset':'5 synthetic images pairs, one shared generated layout; no real photographs',
            'limitations':'Totals vary independently from item rows to test visual reading, not invoice arithmetic. '
                           'No population accuracy, CER on full documents, or calibrated confidence claim.',
            'cases':rows,'raw_exact':sum(x['raw_ocr']==x['expected_amount'] for x in rows),
            'fixed_exact':sum(x['fixed_pipeline']==x['expected_amount'] for x in rows),
            'two_photo_exact':sum(x['exact_match'] for x in rows),
            'median_recovery_ms':statistics.median(x['elapsed_ms'] for x in rows)}
    path=ROOT/'docs/benchmark-synthetic.json'
    path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('Saved',path)


if __name__=='__main__':main()
