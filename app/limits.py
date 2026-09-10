"""Bounded request bodies and optional password for hosted demos."""
import base64
import binascii
import hmac
import os

from starlette.responses import JSONResponse


class RequestPolicy:
    def __init__(self,app):
        self.app=app

    async def __call__(self,scope,receive,send):
        if scope['type']!='http':
            return await self.app(scope,receive,send)
        headers=dict(scope['headers'])
        password=os.getenv('SCANPILOT_PASSWORD','')
        if password and scope['path']!='/api/health':
            valid=False
            try:
                method, token=headers.get(b'authorization',b'').split(b' ',1)
                credentials=base64.b64decode(token,validate=True)
                valid=method.lower()==b'basic' and hmac.compare_digest(credentials,('scanpilot:'+password).encode())
            except (ValueError,binascii.Error):
                pass
            if not valid:
                return await JSONResponse({'detail':'Masuk dengan akses demo ScanPilot.'},401,
                    headers={'WWW-Authenticate':'Basic realm="ScanPilot", charset="UTF-8"'})(scope,receive,send)
        limit=25*1024*1024
        if scope['path']=='/api/package/export': limit=80*1024*1024
        size_error='Package export must not exceed 80 MB.' if limit>25*1024*1024 else 'Total unggahan maksimal 25 MB.'
        try:
            if int(headers.get(b'content-length',b'0'))>limit:
                return await JSONResponse({'detail':size_error},413)(scope,receive,send)
        except ValueError:
            return await JSONResponse({'detail':'Ukuran request tidak valid.'},400)(scope,receive,send)
        # Buffer at most 25 MB before multipart parsing, including chunked bodies.
        # Never keep this buffer between requests or store document content in logs.
        if scope['method']=='POST':
            chunks=[]
            size=0
            while True:
                message=await receive()
                if message['type']=='http.disconnect':
                    return
                chunk=message.get('body',b'')
                size+=len(chunk)
                if size>limit:
                    return await JSONResponse({'detail':size_error},413)(scope,receive,send)
                chunks.append(chunk)
                if not message.get('more_body',False):
                    break
            body=b''.join(chunks)
            chunks.clear()
            delivered=False

            async def buffered_receive():
                nonlocal delivered,body
                if not delivered:
                    delivered=True
                    content,body=body,b''
                    return {'type':'http.request','body':content,'more_body':False}
                return await receive()
            return await self.app(scope,buffered_receive,send)
        return await self.app(scope,receive,send)
