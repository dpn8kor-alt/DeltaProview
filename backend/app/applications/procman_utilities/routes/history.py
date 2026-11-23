
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.applications.procman_utilities.services.history_service import (
    history_service,
)

router = APIRouter(prefix="/history", tags=["ProcMan - History"])

logger = logging.getLogger(__name__)


@router.get("/")
async def get_comparison_history():
    """
    Retrieve all comparison history records.
    Newest comparisons appear first.
    """
    try:
        return history_service.get_all_records()

    except Exception as exc:
        logger.exception("Failed to retrieve comparison history.")
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve comparison history.",
        ) from exc


@router.get("/{record_id}")
async def get_comparison_history_record(record_id: str):
    """
    Retrieve details of one comparison.
    """
    try:
        record = history_service.get_record(record_id)

        if record is None:
            raise HTTPException(
                status_code=404,
                detail="Comparison history record not found.",
            )

        return record

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception("Failed to retrieve comparison record.")
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve comparison record.",
        ) from exc


@router.get("/{record_id}/download")
async def download_comparison_report(record_id: str):
    """
    Download the Excel report associated with a past comparison.
    """
    try:
        record = history_service.get_record(record_id)

        if record is None:
            raise HTTPException(
                status_code=404,
                detail="Comparison history record not found.",
            )

        if record.get("status") != "success":
            raise HTTPException(
                status_code=404,
                detail="No report is available for this comparison.",
            )

        report_path = history_service.get_report_path(record_id)

        if report_path is None:
            raise HTTPException(
                status_code=404,
                detail="The Excel report is no longer available.",
            )

        return FileResponse(
            path=report_path,
            filename=report_path.name,
            media_type=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
        )

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception("Failed to download comparison report.")
        raise HTTPException(
            status_code=500,
            detail="Unable to download the comparison report.",
        ) from exc
