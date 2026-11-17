
import logging
from typing import Any

import httpx

from app.core.config import settings
from app.shared.confluence_client import ConfluenceClient
from app.applications.create_revision_config.parsers.revision_parser import (
    parse_revision_history_page,
)

logger = logging.getLogger(__name__)


class RevisionService:
    """Retrieves QMS revision history directly through HTTP."""

    def build_history_url(self, page_id: str) -> str:
        base = settings.REVISION_HISTORY_BASE_URL.rstrip("/")
        suffix = settings.REVISION_HISTORY_LANGUAGE_QUERY
        return f"{base}/{page_id}{suffix}"

    def get_page_revisions(self, page_id: str) -> list[dict[str, Any]]:
        if not settings.REVISION_HISTORY_BASE_URL:
            raise ValueError("REVISION_HISTORY_BASE_URL is not configured.")

        try:
            confluence_client = ConfluenceClient()

            with httpx.Client(
                timeout=settings.CONFLUENCE_TIMEOUT_SECONDS,
                verify=confluence_client.create_ssl_context(),
            ) as client:
                response = client.get(
                    self.build_history_url(page_id),
                    headers=confluence_client._auth(),
                )

                response.raise_for_status()

                return parse_revision_history_page(response.text)

        except Exception:
            logger.exception(
                "Unable to retrieve revision history for page %s",
                page_id,
            )
            raise

    @staticmethod
    def select_published_and_history(
        revisions: list[dict[str, Any]],
        history_limit: int = 5,
    ) -> dict[str, Any]:
        # First latest=true item is published.
        # Include at most five latest=false items in QMS response order.
        published = next(
            (
                revision
                for revision in revisions
                if str(revision.get("latest", "")).lower() == "true"
            ),
            None,
        )

        history = [
            revision
            for revision in revisions
            if str(revision.get("latest", "")).lower() == "false"
        ][:history_limit]

        if published is None:
            raise ValueError(
                "Revision history did not contain a latest published revision."
            )

        return {
            "published": published,
            "history": history,
        }
