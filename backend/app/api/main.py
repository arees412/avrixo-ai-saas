from fastapi import APIRouter

from app.api.routes import items, login, private, users, utils
from app.core.config import settings
from app.operations.routes import router as operations_router

api_router = APIRouter()
api_router.include_router(operations_router)
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(items.router)


if settings.FASTAPI_ENV == "development":
    api_router.include_router(private.router)
