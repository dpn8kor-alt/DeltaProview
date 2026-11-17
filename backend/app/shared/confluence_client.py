import base64
import ssl
import httpx
from app.core.config import settings


class ConfluenceClient:
    """Shared Confluence REST client. Credentials stay on the backend."""

    def __init__(self) -> None:
        self.base_url = settings.CONFLUENCE_BASE_URL.rstrip("/")
        self.timeout = settings.CONFLUENCE_TIMEOUT_SECONDS

    def _auth(self):
        if settings.CONFLUENCE_AUTH_MODE.lower() == "basic":
            raw = f"{settings.CONFLUENCE_USERNAME}:{settings.CONFLUENCE_PASSWORD}".encode()
            token = base64.b64encode(raw).decode()
            return {"Authorization": f"Basic {token}"}
        if settings.CONFLUENCE_API_TOKEN:
            return {"Authorization": f"Bearer {settings.CONFLUENCE_API_TOKEN}"}
        return {}

    @staticmethod
    def create_ssl_context() -> ssl.SSLContext:
        return ssl.create_default_context()

    async def get_json(self, path: str, params: dict | None = None) -> dict:
        url = f"{self.base_url}/{path.lstrip('/')}"
        async with httpx.AsyncClient(
            timeout=self.timeout,
            verify=self.create_ssl_context(),
        ) as client:
            response = await client.get(url, headers=self._auth(), params=params)
            response.raise_for_status()
            return response.json()

    async def get_child_pages(self, page_id: str) -> list[dict]:
        payload = await self.get_json(f"/rest/api/content/{page_id}/child/page")
        # TODO: implement Confluence pagination after confirming legacy behavior.
        return payload.get("results", [])

    async def get_page_body(self, page_id: str) -> str:
        payload = await self.get_json(
            f"/rest/api/content/{page_id}", params={"expand": "body.view"}
        )
        return payload.get("body", {}).get("view", {}).get("value", "")
