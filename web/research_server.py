"""Production entry: inherited stock-dashboard APIs plus Liangce research routes."""
import os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'web'));sys.path.insert(0,str(ROOT/'scripts'))
os.environ.setdefault('STOCK_DATA_HOME',str(ROOT/'data'))
from main import app
from research_api import router
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse,FileResponse

app.include_router(router)
origins=[x.strip() for x in os.environ.get('LIANGCE_ALLOWED_ORIGINS','').split(',') if x.strip()]
if origins:app.add_middleware(CORSMiddleware,allow_origins=origins,allow_methods=['GET','POST'],allow_headers=['Authorization','Content-Type'],allow_credentials=False)

@app.middleware('http')
async def public_mode(request,call_next):
    # Public read-only deployments expose research snapshots and read APIs;
    # upstream GET /paper/reset and similar mutation routes are not exposed.
    if os.environ.get('LIANGCE_PUBLIC_MODE')=='1' and request.url.path.startswith('/api/'):
        allowed=request.url.path.startswith('/api/research/') or request.url.path=='/api/health'
        if not allowed:return JSONResponse({'detail':'此公开部署只开放研究接口'},status_code=403)
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff';response.headers['Referrer-Policy']='strict-origin-when-cross-origin'
    return response

@app.get('/research/{filename}')
def static_research(filename:str):
    from research_api import ARCHIVE
    p=ARCHIVE/filename
    if p.parent.resolve()!=ARCHIVE.resolve() or not p.is_file():return JSONResponse({'detail':'Not found'},status_code=404)
    return FileResponse(p)

@app.get('/liangce.svg')
def product_icon():
    return FileResponse(ROOT/'frontend/public/liangce.svg',media_type='image/svg+xml')

@app.get('/index.html')
def app_shell():
    return FileResponse(ROOT/'web/dist/index.html',media_type='text/html')

if __name__=='__main__':
    import uvicorn
    uvicorn.run(app,host=os.environ.get('HOST','127.0.0.1'),port=int(os.environ.get('PORT','8810')))
