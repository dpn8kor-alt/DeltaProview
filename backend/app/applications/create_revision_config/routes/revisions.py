from fastapi import APIRouter, HTTPException
from app.applications.create_revision_config.services.revision_service import RevisionService

router = APIRouter(prefix="/revisions", tags=["Revision Config - History"])
service = RevisionService()


@router.get("/{page_id}")
async def get_revision_history(page_id: str):
    try:
        revisions = service.get_page_revisions(page_id)
        return service.select_published_and_history(revisions)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Revision history retrieval failed: {exc}") from exc
