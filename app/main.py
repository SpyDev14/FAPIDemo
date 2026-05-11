from fastapi import FastAPI, Request
import uvicorn

from app.core.config import settings

app = FastAPI(
    debug=settings.DEBUG,
)

@app.get('/')
async def home_route(request: Request):
    i = 0
    for i in range(2000):
        pass
    return {'ok': True, 'msg': f'Банька парилка, кипяток и данилка {i}'}

if __name__ == '__main__':
    uvicorn.run(app)
