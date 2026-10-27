from fastapi import APIRouter

from app.api.v1 import auth, banks, dashboard, donors, meta, search

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(meta.router)
api_router.include_router(dashboard.router)
api_router.include_router(donors.router)
api_router.include_router(banks.router)
api_router.include_router(search.router)
