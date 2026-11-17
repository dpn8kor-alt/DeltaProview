from fastapi import APIRouter, UploadFile, File, HTTPException

from app.applications.procman_utilities.services.configuration_service import (
    ConfigurationService,
)

router = APIRouter(
    prefix="/configuration",
    tags=["ProcMan - Revision Configuration"],
)

configuration_service = ConfigurationService()


@router.get("/pages")
async def list_configured_pages():
    return configuration_service.list_pages()


@router.post("/upload")
async def upload_revision_configuration(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".xml"):
        raise HTTPException(
            status_code=400,
            detail="Please upload an XML file.",
        )

    xml_content = await file.read()

    try:
        return configuration_service.upload_configuration(xml_content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/pages/{page_id}/revisions")
async def get_configured_revisions(page_id: str):
    try:
        return configuration_service.get_page_revisions(page_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))