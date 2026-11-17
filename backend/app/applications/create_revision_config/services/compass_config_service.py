from app.shared.confluence_client import ConfluenceClient
from app.applications.create_revision_config.parsers.page_title_parser import normalize_page_title


class CompassConfigService:
    def __init__(self):
        self.confluence = ConfluenceClient()

    async def get_children_for_level2_pages(self, level2_page_ids: list[str]) -> list[dict]:
        all_children: list[dict] = []
        for page_id in level2_page_ids:
            children = await self.confluence.get_child_pages(page_id)
            # Original application only generated a page node when a parent had >1 child.
            if len(children) > 1:
                for child in children:
                    all_children.append({
                        "id": str(child["id"]),
                        "title": normalize_page_title(child.get("title", "")),
                    })
        return all_children
