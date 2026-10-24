"""Exercise a running deployment with synthetic documents only."""
import argparse
import base64
import io
import json
import os
from pathlib import Path
import httpx
from pypdf import PdfReader


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',default='http://127.0.0.1:8877')
    args=parser.parse_args()
    password=os.environ.get('SCANPILOT_PASSWORD')
    auth=('scanpilot',password) if password else None
    with httpx.Client(base_url=args.url,timeout=180,auth=auth) as client:
        health=client.get('/api/health');health.raise_for_status()
        assert health.json()['pdf']
        first=client.get('/api/sample/covered?lang=en');first.raise_for_status()
        second=client.get('/api/sample/second?lang=en');second.raise_for_status()
        inspection=client.post('/api/analyze',files={'file':('first.jpg',first.content,'image/jpeg')})
        inspection.raise_for_status();assert inspection.json()['regions']
        recovery=client.post('/api/recover',files={'first':('first.jpg',first.content,'image/jpeg'),'second':('second.jpg',second.content,'image/jpeg')})
        recovery.raise_for_status();result=recovery.json()
        assert result['recovered_count']>=1
        assert any(line['source']=='photo-2' for line in result['lines'])
        image=base64.b64decode(result['result'].split(',',1)[1])
        exported=client.post('/api/package/export',files={'images':('page.jpg',image,'image/jpeg')},data={'manifest':json.dumps([{'page':0,'image':0}]),'report':json.dumps({'smoke_test':True})})
        exported.raise_for_status()
        pdf=PdfReader(io.BytesIO(exported.content))
        assert len(pdf.pages)==1 and 'scanpilot-review.json' in pdf.attachments
        imported=client.post('/api/package/import',files={'file':('smoke.pdf',exported.content,'application/pdf')})
        imported.raise_for_status();assert len(imported.json()['pages'])==1
        print(json.dumps({'health':health.json(),'recovered_regions':result['recovered_count'],'pdf_export_import':'passed'}))


if __name__=='__main__':main()
