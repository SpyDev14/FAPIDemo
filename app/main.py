from fastapi.responses import RedirectResponse
from fastapi           import FastAPI
import uvicorn

from app.core.config import settings
from app.api         import api_router

# Я специально сделал передачу аргументов многострочной с запятой в конце,
# чтобы добавление новых параметров вызывало минимум git конфликтов
app = FastAPI(
    debug=settings.DEBUG,
)
app.include_router(api_router)

@app.get('/')
async def redirect_to_docs_route():
    return RedirectResponse('/docs')

if __name__ == '__main__':
    uvicorn.run(app)
