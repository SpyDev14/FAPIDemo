from fastapi.responses import RedirectResponse
from fastapi           import FastAPI
import uvicorn

from app.core.config import settings

app = FastAPI(
    debug=settings.DEBUG,
)

@app.get('/')
async def home_route():
    return RedirectResponse('/docs')

if __name__ == '__main__':
    uvicorn.run(app)
