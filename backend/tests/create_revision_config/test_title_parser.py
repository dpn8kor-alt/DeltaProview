from app.applications.create_revision_config.parsers.page_title_parser import normalize_page_title


def test_uuid_prefix_removed():
    assert normalize_page_title("12345678-1234-1234-1234-123456789abc_My Page") == "My Page"


def test_normal_title_unchanged():
    assert normalize_page_title("My Page") == "My Page"
