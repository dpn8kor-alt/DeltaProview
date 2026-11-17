from fastapi import APIRouter
from app.applications.create_revision_config.routes import pages, revisions, xml_config

router = APIRouter(tags=["CreateRevisionConfig"])
router.include_router(pages.router)
router.include_router(revisions.router)
router.include_router(xml_config.router)
