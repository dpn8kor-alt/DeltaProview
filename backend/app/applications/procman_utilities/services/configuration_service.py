import json
import xml.etree.ElementTree as ET
from pathlib import Path

from app.core.config import settings


class ConfigurationService:
    def __init__(self):
        self.output_dir = Path(settings.OUTPUT_DIR)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.storage_file = self.output_dir / "procman_configuration.json"

    @staticmethod
    def parse_configuration(xml_content: bytes) -> dict:
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as exc:
            raise ValueError(f"Invalid XML file: {exc}") from exc

        if root.tag != "Confluence_Page_Tree":
            raise ValueError("Expected XML root element: Confluence_Page_Tree")

        pages = {}

        for page in root.findall("Confluence_Page"):
            name = page.findtext("Page_Name")
            page_id = page.findtext("Pub_Page_Id")

            if not name or not page_id:
                raise ValueError("Each page must contain Page_Name and Pub_Page_Id.")

            revisions = []

            revision_container = page.find("Page_Revisions")
            if revision_container is not None:
                for revision in revision_container.findall("Page_Revision"):
                    revision_name = revision.findtext("Revision")
                    revision_id = revision.findtext("Rev_Page_Id")

                    if revision_name and revision_id:
                        revisions.append({
                            "revision": revision_name,
                            "revision_page_id": revision_id,
                        })

            pages[page_id] = {
                "page_name": name,
                "published_page_id": page_id,
                "revisions": revisions,
            }

        if not pages:
            raise ValueError("The XML file does not contain any valid pages.")

        return pages

    def upload_configuration(self, xml_content: bytes) -> dict:
        pages = self.parse_configuration(xml_content)
        data = {"pages": pages}

        self.storage_file.write_text(
            json.dumps(data, indent=4),
            encoding="utf-8",
        )

        return {
            "message": "Revision configuration uploaded successfully.",
            "total_pages": len(pages),
            "storage_file": str(self.storage_file),
        }

    def get_page_revisions(self, page_id: str) -> dict:
        if not self.storage_file.exists():
            raise ValueError("No revision configuration has been uploaded.")

        data = json.loads(self.storage_file.read_text(encoding="utf-8"))
        page = data["pages"].get(page_id)

        if page is None:
            raise ValueError(f"Page ID {page_id} was not found in the configuration.")

        return page

    def list_pages(self) -> list[dict]:
        if not self.storage_file.exists():
            return []

        data = json.loads(self.storage_file.read_text(encoding="utf-8"))
        return [
            {"page_id": page_id, **page}
            for page_id, page in data.get("pages", {}).items()
        ]