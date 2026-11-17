from xml.etree import ElementTree as ET
from app.applications.create_revision_config.services.xml_generation_service import RevisionXmlGenerationService


def test_revision_xml_includes_published_and_five_historical():
    revisions = [{"version": "6", "pageId": "p6", "latest": "true"}] + [
        {"version": str(i), "pageId": f"p{i}", "latest": "false"} for i in range(5, 0, -1)
    ]
    xml = RevisionXmlGenerationService().generate_revision_xml([
        {"title": "A & B", "revisions": revisions}
    ])
    root = ET.fromstring(xml)
    page = root.find("Confluence_Page")
    assert page.findtext("Page_Name") == "A & B"
    assert page.findtext("Pub_Page_Id") == "p6"
    assert len(page.findall("./Page_Revisions/Page_Revision")) == 5


def test_revision_xml_skips_pages_with_one_revision():
    xml = RevisionXmlGenerationService().generate_revision_xml([
        {"title": "Only one", "revisions": [{"latest": "true", "pageId": "1"}]}
    ])
    assert len(ET.fromstring(xml)) == 0


def test_compass_xml_escapes_ampersands_safely():
    xml = RevisionXmlGenerationService().generate_compass_xml([
        {"id": "123", "title": "A & B"}
    ])
    root = ET.fromstring(xml)
    assert root.findtext("./Confluence_Page/Page_Name") == "A & B"
