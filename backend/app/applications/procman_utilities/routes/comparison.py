
import base64
import json
import logging
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from app.applications.create_revision_config.services.revision_service import RevisionService
from app.applications.create_revision_config.services.xml_generation_service import (
    RevisionXmlGenerationService,
)
from app.applications.procman_utilities.services.configuration_service import (
    ConfigurationService,
)
from app.applications.procman_utilities.services.page_content_service import (
    ProcessPageContentService,
)
from app.applications.procman_utilities.services.comparison_service import (
    ProcessComparisonService,
)
from app.applications.procman_utilities.services.report_service import (
    ProcessComparisonReportService,
)
from app.applications.procman_utilities.services.history_service import (
    history_service,
)

router = APIRouter(prefix="/comparison", tags=["ProcMan - Comparison"])

logger = logging.getLogger(__name__)


class ComparisonRequest(BaseModel):
    published_page_id: str
    outdated_page_id: str
    method_name: str | None = None
    published_version: str | None = None
    outdated_version: str | None = None


async def get_comparison_result(request: ComparisonRequest):
    page_service = ProcessPageContentService()

    published_html = await page_service.fetch_process_page_html(
        request.published_page_id
    )
    outdated_html = await page_service.fetch_process_page_html(
        request.outdated_page_id
    )

    return compare_content(request, published_html, outdated_html)


def compare_content(request, published_html, outdated_html):
    page_service = ProcessPageContentService()

    published_activities = page_service.parse_process_table(
        published_html,
        request.published_page_id,
    )

    outdated_activities = page_service.parse_process_table(
        outdated_html,
        request.outdated_page_id,
    )

    return ProcessComparisonService().compare(
        published_activities,
        outdated_activities,
    )


class WorkflowRequest(ComparisonRequest):
    method_page_id: str
    published_version: str
    outdated_version: str


def revision_payload(request: WorkflowRequest):
    configured = next(
        (
            page
            for page in ConfigurationService().list_pages()
            if page["page_id"] == request.method_page_id
        ),
        None,
    )

    if configured is None:
        revisions = RevisionService().get_page_revisions(
            request.method_page_id
        )
    else:
        revisions = [
            {
                "latest": True,
                "pageId": configured["published_page_id"],
            }
        ]

        selected = {
            request.published_page_id,
            request.outdated_page_id,
        }

        revisions.extend(
            {
                "latest": False,
                "pageId": item["revision_page_id"],
                "version": item["revision"],
            }
            for item in configured["revisions"]
            if item["revision_page_id"] in selected
        )

    return [
        {
            "title": request.method_name or request.method_page_id,
            "revisions": revisions,
        }
    ]


def resolve_selection(payload, request):
    xml = RevisionXmlGenerationService().generate_revision_xml(payload)

    page, = ConfigurationService.parse_configuration(xml).values()

    available = {
        (item["revision_page_id"], item["revision"]): item["revision_page_id"]
        for item in page["revisions"]
    }

    available[
        (page["published_page_id"], "Published")
    ] = page["published_page_id"]

    try:
        return (
            available[
                (request.published_page_id, request.published_version)
            ],
            available[
                (request.outdated_page_id, request.outdated_version)
            ],
        )
    except KeyError as exc:
        raise ValueError(
            "The selected revisions are no longer available. Reload the method."
        ) from exc


def event(**fields):
    return json.dumps(fields) + "\n"


async def save_history(
    request: WorkflowRequest,
    status: str,
    report_path: str | None = None,
    error: str | None = None,
):
    """
    Save a workflow attempt without interrupting the comparison
    if history persistence encounters an error.
    """
    try:
        await run_in_threadpool(
            history_service.create_record,
            page_id=request.method_page_id,
            page_name=request.method_name or request.method_page_id,
            source_version=request.published_version,
            target_version=request.outdated_version,
            status=status,
            report_path=report_path,
            error=error,
        )
    except Exception:
        logger.exception("Could not save comparison history.")


@router.post("/workflow")
async def run_workflow(request: WorkflowRequest):
    if request.published_page_id == request.outdated_page_id:
        raise HTTPException(
            422,
            "Select two different revisions.",
        )

    async def events():
        stage = "Fetching Process Compass content"
        report_path = None

        try:
            yield event(stage=stage)

            payload = await run_in_threadpool(
                revision_payload,
                request,
            )

            content = ProcessPageContentService()
            html = {}

            for page_id in (
                request.published_page_id,
                request.outdated_page_id,
            ):
                html[page_id] = await content.fetch_process_page_html(
                    page_id
                )

            stage = "Generating XML internally"
            yield event(stage=stage)

            newer, older = resolve_selection(payload, request)

            stage = "Comparing versions"
            yield event(stage=stage)

            result = await run_in_threadpool(
                compare_content,
                request,
                html[newer],
                html[older],
            )

            stage = "Generating the report"
            yield event(stage=stage)

            # Generate the report in persistent storage.
            # Do not use TemporaryDirectory here because the report
            # must remain available for future history downloads.
            report_path = await run_in_threadpool(
                ProcessComparisonReportService().generate_report,
                result,
                request.method_name or "",
                request.published_version,
                request.outdated_version,
                os.getenv("CONFLUENCE_BASE_URL", ""),
            )

            report_file = Path(report_path)

            if not report_file.is_file():
                raise FileNotFoundError(
                    "Generated Excel report could not be found."
                )

            with open(report_file, "rb") as workbook:
                while chunk := workbook.read(49152):
                    yield event(
                        data=base64.b64encode(chunk).decode("ascii")
                    )

            # Save successful comparison after report generation
            # and report streaming have completed.
            await save_history(
                request=request,
                status="success",
                report_path=str(report_file.resolve()),
            )

            yield event(ready=True)

        except Exception as exc:
            logger.exception("%s failed", stage)

            detail = (
                str(exc)
                if isinstance(exc, (ValueError, FileNotFoundError))
                else "Check the backend connection and logs."
            )

            error_message = f"{stage} failed: {detail}"

            # Save failed comparison attempts as well.
            await save_history(
                request=request,
                status="failed",
                report_path=report_path,
                error=error_message,
            )

            yield event(error=error_message)

    return StreamingResponse(
        events(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-store",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/preview")
async def preview_comparison(request: ComparisonRequest):
    try:
        return await get_comparison_result(request)

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

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
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Excel report generation failed: {str(exc)}",
        )
