from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.core.temp_storage import get_temp_download_dir
from app.applications.create_revision_config.services.revision_service import RevisionService
from app.applications.create_revision_config.services.xml_generation_service import RevisionXmlGenerationService
from app.applications.create_revision_config.services.compass_config_service import CompassConfigService

router = APIRouter(prefix="/xml", tags=["Revision Config - XML"])
revision_service = RevisionService()
xml_service = RevisionXmlGenerationService()


def _xml_download(content: bytes, filename: str) -> FileResponse:
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    stored_name = f"{Path(filename).stem}_{timestamp}_{uuid4().hex[:8]}.xml"
    file_path = get_temp_download_dir() / stored_name
    file_path.write_bytes(content)
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/xml",
    )


class SelectedPage(BaseModel):
    id: str
    title: str


class RevisionXmlRequest(BaseModel):
    pages: list[SelectedPage] = Field(min_length=1)


class CompassXmlRequest(BaseModel):
    level2_page_ids: list[str] = Field(min_length=1)


@router.post("/revision")
async def generate_revision_config(request: RevisionXmlRequest):
    try:
        page_payloads = []
        for page in request.pages:
            revisions = revision_service.get_page_revisions(page.id)
            page_payloads.append({
                "id": page.id,
                "title": page.title,
                "revisions": revisions,
            })
        content = xml_service.generate_revision_xml(page_payloads)
        return _xml_download(content, "output.xml")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Revision XML generation failed: {exc}") from exc


@router.post("/compass")
async def generate_compass_config(request: CompassXmlRequest):
    try:
        pages = await CompassConfigService().get_children_for_level2_pages(request.level2_page_ids)
        content = xml_service.generate_compass_xml(pages)
        return _xml_download(content, "Confluence_Page_Config.xml")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Compass XML generation failed: {exc}") from exc
