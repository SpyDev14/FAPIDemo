from fastapi.responses import RedirectResponse
from fastapi           import FastAPI
import uvicorn

from app.core.config import settings, setup_logging
from app.api         import api_router

app = FastAPI(
    debug=settings.DEBUG,
    on_startup=[
        setup_logging,
    ]
)
app.include_router(api_router)

@app.get('/')
async def redirect_to_docs_route():
    return RedirectResponse('/docs')

if __name__ == '__main__':
    uvicorn.run(app)
