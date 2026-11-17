
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.applications.procman_utilities.services.page_content_service import (
    ProcessPageContentService,
)
from app.applications.procman_utilities.services.comparison_service import (
    ProcessComparisonService,
)
from app.applications.procman_utilities.services.report_service import (
    ProcessComparisonReportService,
)

router = APIRouter(prefix="/comparison", tags=["ProcMan - Comparison"])


class ComparisonRequest(BaseModel):
    published_page_id: str
    outdated_page_id: str
    method_name: str | None = None
    published_version: str | None = None
    outdated_version: str | None = None


async def get_comparison_result(request: ComparisonRequest):
    page_service = ProcessPageContentService()
    comparison_service = ProcessComparisonService()

    published_html = await page_service.fetch_process_page_html(
        request.published_page_id
    )
    outdated_html = await page_service.fetch_process_page_html(
        request.outdated_page_id
    )

    published_activities = page_service.parse_process_table(
        published_html,
        request.published_page_id,
    )
    outdated_activities = page_service.parse_process_table(
        outdated_html,
        request.outdated_page_id,
    )

    return comparison_service.compare(
        published_activities,
        outdated_activities,
    )


@router.post("/preview")
async def preview_comparison(request: ComparisonRequest):
    try:
        return await get_comparison_result(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Process-flow comparison failed: {str(exc)}",
        )


@router.post("/report")
async def generate_comparison_report(request: ComparisonRequest):
    try:
        comparison_result = await get_comparison_result(request)

        report_service = ProcessComparisonReportService()

        report_path = report_service.generate_report(
            comparison_result=comparison_result,
            method_name=request.method_name or "",
            published_version=request.published_version or "",
            outdated_version=request.outdated_version or "",
            confluence_base_url=os.getenv("CONFLUENCE_BASE_URL", ""),
        )

        file_path = Path(report_path)

        if not file_path.exists():
            raise HTTPException(
                status_code=500,
                detail="Excel report could not be found after generation.",
            )

        return FileResponse(
            path=file_path,
            filename=file_path.name,
            media_type=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
        )

    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Excel report generation failed: {str(exc)}",
        )
