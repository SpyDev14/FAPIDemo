from fastapi.responses import RedirectResponse
from fastapi           import FastAPI, Response

from app.core.config import settings, setup_logging
from app.api         import api_router

app = FastAPI(
    debug=settings.DEBUG,
    on_startup=[
        setup_logging,
    ]
)
app.include_router(api_router)


@app.get('/health')
async def healthcheck():
    return Response(status_code=200)

@app.get('/')
async def redirect_to_docs():
    return RedirectResponse('/docs')
