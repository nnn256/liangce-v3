"""Small FastAPI entry for free hosting: no market/scientific imports at boot.

Shares the verified research router and lazy-loads the existing quote gateway
only when requested. Bundled frontend and source snapshots survive cold starts;
new ephemeral jobs are explicitly advertised as temporary.
"""
from pathlib import Path
import os,sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'web'));sys.path.insert(0,str(ROOT/'scripts'))
from fastapi import FastAPI,HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse,JSONResponse
from fastapi.staticfiles import StaticFiles
from web.research_api import router,ARCHIVE,health

app=FastAPI(title='量测 v3 · 免费托管研究API',version='3.0.0')
app.add_middleware(GZipMiddleware,minimum_size=1024)
origins=[x.strip().rstrip('/') for x in os.environ.get('LIANGCE_ALLOWED_ORIGINS','https://nnn256.github.io').split(',') if x.strip()]
app.add_middleware(CORSMiddleware,allow_origins=origins,allow_methods=['GET','POST'],allow_headers=['Authorization','Content-Type'],expose_headers=['ETag'],allow_credentials=False)
app.include_router(router)
DIST=ROOT/'web/dist'
if (DIST/'assets').is_dir():app.mount('/assets',StaticFiles(directory=str(DIST/'assets')),name='assets')


@app.middleware('http')
async def security_headers(request,call_next):
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='strict-origin-when-cross-origin'
    if request.url.path in {'/','/index.html','/sw.js'}:
        response.headers['Cache-Control']='no-cache, must-revalidate'
    return response


@app.get('/api/health')
def health_alias():return health()


@app.get('/')
@app.get('/index.html')
def home():
    if (DIST/'index.html').is_file():return FileResponse(DIST/'index.html')
    return {'product':'量测 v3','status':'ok','frontend':'https://nnn256.github.io/liangce-v3/','health':'/api/research/health'}


@app.get('/research/{filename}')
def research_asset(filename:str):
    target=(ARCHIVE/filename).resolve()
    if target.parent!=ARCHIVE.resolve() or not target.is_file():raise HTTPException(404,'归档文件不存在')
    return FileResponse(target)


@app.get('/{filename}')
def app_asset(filename:str):
    allowed={'liangce.svg','icon.svg','manifest.webmanifest','registerSW.js','sw.js','pwa-192x192.png','pwa-512x512.png','pwa-maskable-512x512.png','apple-touch-icon.png'}
    if filename not in allowed and not (filename.startswith('workbox-') and filename.endswith('.js')):raise HTTPException(404,'Not found')
    target=(DIST/filename).resolve()
    if target.parent!=DIST.resolve() or not target.is_file():raise HTTPException(404,'Not found')
    return FileResponse(target)
