from fastapi.testclient import TestClient

from app.applications.create_revision_config.routes import xml_config
from app.main import app


def test_revision_and_compass_xml_are_saved_to_shared_temp_directory(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(xml_config, "get_temp_download_dir", lambda: tmp_path)
    monkeypatch.setattr(
        xml_config.revision_service,
        "get_page_revisions",
        lambda page_id: [
            {"version": "2.0", "pageId": page_id, "latest": "true"},
            {"version": "1.0", "pageId": "old-page", "latest": "false"},
        ],
    )

    async def get_children(self, level2_page_ids):
        return [{"id": "child-page", "title": "Child page"}]

    monkeypatch.setattr(
        xml_config.CompassConfigService,
        "get_children_for_level2_pages",
        get_children,
    )

    with TestClient(app) as client:
        revision_response = client.post(
            "/api/v1/revision-config/xml/revision",
            json={"pages": [{"id": "published-page", "title": "Test page"}]},
        )
        compass_response = client.post(
            "/api/v1/revision-config/xml/compass",
            json={"level2_page_ids": ["process-page"]},
        )

    assert revision_response.status_code == 200
    assert compass_response.status_code == 200
    assert revision_response.headers["content-disposition"].endswith('filename="output.xml"')
    assert compass_response.headers["content-disposition"].endswith(
        'filename="Confluence_Page_Config.xml"'
    )
    assert len(list(tmp_path.glob("*.xml"))) == 2