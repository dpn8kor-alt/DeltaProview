from xml.etree import ElementTree as ET


class RevisionXmlGenerationService:
    """XML generation preserving the original Confluence_Page_Tree schema."""

    @staticmethod
    def _sub(parent: ET.Element, tag: str, value: str | None = None) -> ET.Element:
        child = ET.SubElement(parent, tag)
        if value is not None:
            child.text = str(value)
        return child

    def generate_revision_xml(self, selected_pages: list[dict]) -> bytes:
        root = ET.Element("Confluence_Page_Tree")
        for page in selected_pages:
            revisions = page.get("revisions", [])
            if len(revisions) <= 1:
                continue

            selected = self._select(revisions)
            node = ET.SubElement(root, "Confluence_Page")
            self._sub(node, "Page_Name", page["title"])
            self._sub(node, "Pub_Page_Id", str(selected["published"]["pageId"]))
            history_node = ET.SubElement(node, "Page_Revisions")
            for revision in selected["history"]:
                rev_node = ET.SubElement(history_node, "Page_Revision")
                self._sub(rev_node, "Revision", revision.get("version", ""))
                self._sub(rev_node, "Rev_Page_Id", str(revision.get("pageId", "")))
        return self._serialize(root)

    def generate_compass_xml(self, child_pages: list[dict]) -> bytes:
        root = ET.Element("Confluence_Page_Tree")
        for page in child_pages:
            node = ET.SubElement(root, "Confluence_Page")
            self._sub(node, "Page_Name", page["title"])
            self._sub(node, "Pub_Page_Id", str(page["id"]))
        return self._serialize(root)

    @staticmethod
    def _select(revisions: list[dict]) -> dict:
        from app.applications.create_revision_config.services.revision_service import RevisionService
        return RevisionService.select_published_and_history(revisions)

    @staticmethod
    def _serialize(root: ET.Element) -> bytes:
        ET.indent(root, space="  ")
        return ET.tostring(root, encoding="utf-8", xml_declaration=True)
