"""Top-level API router."""

from fastapi import APIRouter

from app.api.routes.audit_log import router as audit_log_router
from app.api.routes.auth import router as auth_router
from app.api.routes.classes import router as classes_router
from app.api.routes.evaluation import router as evaluation_router
from app.api.routes.health import router as health_router
from app.api.routes.reports import router as reports_router
from app.api.routes.settings import router as settings_router
from app.api.routes.submissions import router as submissions_router
from app.api.routes.users import router as users_router

api_router = APIRouter()
api_router.include_router(audit_log_router)
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(classes_router)
api_router.include_router(submissions_router)
api_router.include_router(evaluation_router)
api_router.include_router(reports_router)
api_router.include_router(settings_router)
api_router.include_router(users_router)
