
from fastapi import APIRouter

from app.core.config import settings
from app.shared.confluence_client import ConfluenceClient
from app.shared.models import ConfluencePage
from app.applications.create_revision_config.parsers.page_title_parser import (
    normalize_page_title,
)

router = APIRouter(prefix="/pages", tags=["ProcMan - Pages"])


@router.get("/root")
async def get_root_pages():
    rows = await ConfluenceClient().get_child_pages(
        settings.PROCESS_LANDSCAPE_ROOT_PAGE_ID
    )

    return [
        ConfluencePage(
            id=str(x["id"]),
            title=normalize_page_title(x["title"]),
            type=x.get("type"),
            status=x.get("status"),
        )
        for x in rows
    ]


@router.get("/{page_id}/children")
async def get_child_pages(page_id: str):
    rows = await ConfluenceClient().get_child_pages(page_id)

    return [
        ConfluencePage(
            id=str(x["id"]),
            title=normalize_page_title(x["title"]),
            type=x.get("type"),
            status=x.get("status"),
        )
        for x in rows
    ]
@router.get("/{page_id}/html")
async def get_page_html(page_id: str):
    html = await ConfluenceClient().get_page_body(page_id)

    return {
        "page_id": page_id,
        "html": html,
    }
