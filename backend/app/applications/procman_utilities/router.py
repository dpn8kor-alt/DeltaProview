
from fastapi import APIRouter

from app.applications.procman_utilities.routes import (
    pages,
    configuration,
    comparison,
    history,
)

router = APIRouter(tags=["ProcManUtilities"])

router.include_router(pages.router)
router.include_router(configuration.router)
router.include_router(comparison.router)
router.include_router(history.router)
