
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

        confluence_client = ConfluenceClient()
        url = self.build_history_url(page_id)

        # Allow more time for Confluence to return revision history.
        timeout = httpx.Timeout(
            connect=10.0,
            read=60.0,
            write=10.0,
            pool=10.0,
        )

        try:
            with httpx.Client(
                timeout=timeout,
                verify=confluence_client.create_ssl_context(),
            ) as client:

                logger.info(
                    "Fetching revision history for page ID: %s",
                    page_id,
                )

                response = client.get(
                    url,
                    headers=confluence_client._auth(),
                )

                logger.info(
                    "Revision history response status: %s",
                    response.status_code,
                )

                response.raise_for_status()

                revisions = parse_revision_history_page(response.text)

                logger.info(
                    "Successfully retrieved %s revisions for page %s",
                    len(revisions),
                    page_id,
                )

                return revisions

        except httpx.ReadTimeout:
            logger.exception(
                "Confluence read timeout while fetching revision history "
                "for page %s. URL: %s",
                page_id,
                url,
            )
            raise

        except httpx.HTTPStatusError as exc:
            logger.error(
                "Confluence returned HTTP %s for page %s. Response: %s",
                exc.response.status_code,
                page_id,
                exc.response.text[:2000],
            )
            raise

        except httpx.RequestError:
            logger.exception(
                "Network error while fetching revision history for page %s",
                page_id,
            )
            raise

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
        published = next(
            (
                revision
                for revision in revisions
                if str(revision.get("latest", "")).lower() == "true"
            ),
            None,
        )

        # Include at most five latest=false items.
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
