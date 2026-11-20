
import base64
import ssl
import logging
import httpx

from app.core.config import settings


logger = logging.getLogger(__name__)


class ConfluenceClient:
    """Shared Confluence REST client. Credentials stay on the backend."""

    def __init__(self) -> None:
        self.base_url = settings.CONFLUENCE_BASE_URL.rstrip("/")
        self.timeout = settings.CONFLUENCE_TIMEOUT_SECONDS

    def _auth(self) -> dict:
        """Generate authentication headers."""

        if settings.CONFLUENCE_AUTH_MODE.lower() == "basic":
            raw = (
                f"{settings.CONFLUENCE_USERNAME}:"
                f"{settings.CONFLUENCE_PASSWORD}"
            ).encode()

            token = base64.b64encode(raw).decode()

            return {
                "Authorization": f"Basic {token}"
            }

        if settings.CONFLUENCE_API_TOKEN:
            return {
                "Authorization": f"Bearer {settings.CONFLUENCE_API_TOKEN}"
            }

        return {}

    @staticmethod
    def create_ssl_context() -> ssl.SSLContext:
        """Create SSL context."""

        return ssl.create_default_context()

    async def get_json(
        self,
        path: str,
        params: dict | None = None
    ) -> dict:
        """Send GET request and return JSON response."""

        url = f"{self.base_url}/{path.lstrip('/')}"

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                verify=self.create_ssl_context(),
            ) as client:

                response = await client.get(
                    url,
                    headers=self._auth(),
                    params=params
                )

                if response.is_error:
                    logger.error(
                        "Confluence API error | URL: %s | Status: %s | Response: %s",
                        response.request.url,
                        response.status_code,
                        response.text[:2000]
                    )

                response.raise_for_status()

                return response.json()

        except httpx.HTTPStatusError as exc:
            logger.exception(
                "Confluence returned HTTP %s for %s",
                exc.response.status_code,
                exc.request.url
            )
            raise

        except httpx.RequestError:
            logger.exception(
                "Unable to connect to Confluence: %s",
                url
            )
            raise

        except ValueError:
            logger.exception(
                "Invalid JSON response received from Confluence: %s",
                url
            )
            raise

    async def get_child_pages(self, page_id: str) -> list[dict]:
        """Fetch all child pages using pagination."""

        all_pages = []
        start = 0
        limit = 100

        while True:
            payload = await self.get_json(
                f"/rest/api/content/{page_id}/child/page",
                params={
                    "start": start,
                    "limit": limit
                }
            )

            results = payload.get("results", [])

            if not results:
                break

            all_pages.extend(results)

            if len(results) < limit:
                break

            start += len(results)

        return all_pages

    async def get_page_body(self, page_id: str) -> str:
        """Fetch the rendered body of a Confluence page."""

        payload = await self.get_json(
            f"/rest/api/content/{page_id}",
            params={
                "expand": "body.view"
            }
        )

        return (
            payload
            .get("body", {})
            .get("view", {})
            .get("value", "")
        )
