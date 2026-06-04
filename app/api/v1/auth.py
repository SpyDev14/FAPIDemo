from fastapi import APIRouter

router = APIRouter(prefix='/auth')

# POST  /api/v1/auth/login
# POST  /api/v1/auth/refresh (req: user)
