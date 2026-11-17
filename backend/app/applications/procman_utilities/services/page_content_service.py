import re

from bs4 import BeautifulSoup, Tag

from app.shared.confluence_client import ConfluenceClient


class ProcessPageContentService:
    """Fetches and parses Process Compass pages."""

    BASE_URL = "https://kms.wam-sso.bosch.com"

    HASH_PATTERN = re.compile(
        r"\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b",
        re.IGNORECASE,
    )

    async def fetch_process_page_html(self, page_id: str) -> str:
        return await ConfluenceClient().get_page_body(page_id)

    @classmethod
    def normalize_url(cls, href: str) -> str:
        """Convert relative Confluence URLs into absolute URLs."""
        if href.startswith("/"):
            return f"{cls.BASE_URL}{href}"
        return href

    @classmethod
    def extract_links(cls, cell: Tag) -> list[dict]:
        """Extract links from a table cell."""
        links = []

        for anchor in cell.find_all("a", href=True):
            links.append({
                "text": anchor.get_text(" ", strip=True).replace("&amp;", "&"),
                "href": cls.normalize_url(anchor["href"]),
            })

        return links

    @classmethod
    def extract_named_items(cls, cell: Tag) -> dict:
        """
        Extract linked and unlinked items.

        Follows the original C# InputDic and OutputDic logic.
        """
        items = {}

        for anchor in cell.find_all("a", href=True):
            name = anchor.get_text(" ", strip=True).replace("&amp;", "&")

            if name:
                items[name] = cls.normalize_url(anchor["href"])

        for list_item in cell.find_all("li"):
            name = list_item.get_text(" ", strip=True).replace("&amp;", "&")

            if name and name not in items:
                items[name] = "IOwithoutLink"

        return items

    @staticmethod
    def _direct_children_until_next_bold(bold: Tag):
        """Yield sibling elements until the next bold heading."""
        sibling = bold.next_sibling

        while sibling is not None:
            if isinstance(sibling, Tag) and sibling.name == "b":
                break

            yield sibling
            sibling = sibling.next_sibling

    @classmethod
    def extract_grouped_items(
        cls,
        cell: Tag,
        group_field: str,
        name_field: str,
        link_field: str,
        dependency_mode: bool = False,
    ) -> list[dict]:
        """
        Extract RASIC or dependency entries.

        Each bold heading represents a role or dependency type.
        Links inside the following div elements belong to that heading.
        """
        records = []

        for heading in cell.find_all("b"):
            heading_text = heading.get_text(" ", strip=True)

            if dependency_mode:
                heading_text = re.sub(r"[()]", "", heading_text)
                heading_text = heading_text.replace("&amp;", " ")

                # Match the original C# Dependent_Items enum.
                group_name = re.sub(
                    r"\s*&\s*",
                    "_",
                    heading_text.strip(),
                )
                group_name = re.sub(r"\s+", "_", group_name)

            else:
                group_name = heading_text

            if not group_name:
                continue

            for sibling in cls._direct_children_until_next_bold(heading):
                if not isinstance(sibling, Tag) or sibling.name != "div":
                    continue

                for anchor in sibling.find_all("a", href=True):
                    item_name = anchor.get_text(
                        " ", strip=True
                    ).replace("&amp;", "&")

                    if not item_name:
                        continue

                    records.append({
                        group_field: group_name,
                        name_field: item_name,
                        link_field: cls.normalize_url(anchor["href"]),
                    })

        return records

    @classmethod
    def clean_activity_text(cls, value: str) -> str:
        """
        Remove the trailing hash identifier from activity titles,
        following the original C# logic.
        """
        value = value.strip()

        if not cls.HASH_PATTERN.search(value):
            return value

        for separator in ("(", "_"):
            index = value.find(separator)

            if index >= 0:
                return value[:index].strip()

        return value

    @classmethod
    def parse_process_table(
        cls,
        html: str,
        page_id: str | None = None,
    ) -> list[dict]:
        """Parse the Process Compass activity table."""

        soup = BeautifulSoup(html, "lxml")

        table = soup.find(
            "table",
            class_="qms-structure-table",
        )

        if table is None:
            page_reference = f" on Confluence page {page_id}" if page_id else ""
            raise ValueError(
                "Process-flow table was not found"
                f"{page_reference}. Select a method page containing the "
                "QMS process-flow table."
            )

        rows = []

        for tr in table.select("tbody tr"):
            cells = tr.find_all("td", recursive=False)

            if len(cells) < 9:
                continue

            page_type = next(
                (
                    element.get("title")
                    for element in cells[1].find_all(True)
                    if element.get("title")
                ),
                "",
            )

            rows.append({
                "Nr": cells[0].get_text(" ", strip=True),
                "type": page_type,
                "Title": cls.clean_activity_text(
                    cells[2].get_text(" ", strip=True)
                ),
                "Next": cls.clean_activity_text(
                    cells[3].get_text(" ", strip=True)
                ),
                "InputDic": cls.extract_named_items(cells[4]),
                "description": cells[5].get_text(" ", strip=True),
                "OutputDic": cls.extract_named_items(cells[6]),
                "RASIC": cls.extract_grouped_items(
                    cells[7],
                    "Role",
                    "RoleName",
                    "RoleLink",
                ),
                "Dependencies": cls.extract_grouped_items(
                    cells[8],
                    "Dep_Type",
                    "Dep_Name",
                    "Dep_Link",
                    dependency_mode=True,
                ),
            })

        return rows