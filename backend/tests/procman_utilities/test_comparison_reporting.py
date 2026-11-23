import base64
import json
from io import BytesIO
from pathlib import Path

from openpyxl import load_workbook
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.applications.procman_utilities.routes import comparison

from app.applications.procman_utilities.services import comparison_service
from app.applications.procman_utilities.services import report_service
from app.applications.procman_utilities.services.page_content_service import (
    ProcessPageContentService,
)


def test_missing_process_table_error_identifies_page():
    with pytest.raises(ValueError, match="Confluence page 1031974009"):
        ProcessPageContentService.parse_process_table(
            "<html><body><table class='confluenceTable'></table></body></html>",
            "1031974009",
        )


def _comparison_result():
    published = [
        {"Nr": "1", "Title": "Unchanged", "Next": "2"},
        {
            "Nr": "2",
            "Title": "Changed",
            "Next": "3",
            "InputDic": {"new input": "new-link"},
            "OutputDic": {"new output": "new-link"},
            "RASIC": [{"Role": "Responsible", "RoleName": "New role"}],
            "Dependencies": [{"Dep_Type": "Instruction", "Dep_Name": "New guide"}],
        },
    ]
    outdated = [
        {"Nr": "1", "Title": "Unchanged", "Next": "2"},
        {
            "Nr": "2",
            "Title": "Changed",
            "Next": "3",
            "InputDic": {"old input": "old-link"},
            "OutputDic": {"old output": "old-link"},
            "RASIC": [{"Role": "Responsible", "RoleName": "Old role"}],
            "Dependencies": [{"Dep_Type": "Instruction", "Dep_Name": "Old guide"}],
        },
    ]

    return comparison_service.ProcessComparisonService().compare(
        published,
        outdated,
    )


def test_unchanged_activities_are_not_counted_as_modified():
    result = _comparison_result()

    assert result["summary"]["activities_modified"] == 1
    assert result["summary"]["inputs_added"] == 1
    assert result["summary"]["inputs_deleted"] == 1
    assert result["summary"]["outputs_added"] == 1
    assert result["summary"]["outputs_deleted"] == 1
    assert result["summary"]["rasic_added"] == 1
    assert result["summary"]["rasic_deleted"] == 1
    assert result["summary"]["dependencies_added"] == 1
    assert result["summary"]["dependencies_deleted"] == 1


def test_excel_summary_counts_and_file_use_temp_directory(monkeypatch, tmp_path):
    monkeypatch.setattr(
        report_service,
        "get_temp_download_dir",
        lambda: tmp_path,
    )

    report_path = Path(
        report_service.ProcessComparisonReportService().generate_report(
            comparison_result=_comparison_result(),
            method_name="Test Method",
            published_version="Published",
            outdated_version="1.0",
        )
    )

    assert report_path.parent == tmp_path

    workbook = load_workbook(report_path, data_only=True)
    summary_sheet = workbook["Info-Summary"]
    assert [summary_sheet.cell(row, 3).value for row in range(10, 19)] == [1] * 9
    assert summary_sheet["A21"].value == "Changed"
    workbook.close()


@pytest.fixture
def workflow(monkeypatch):
    revisions = [dict(latest=True, pageId='30', version='3'),
                 dict(latest=False, pageId='20', version='2'),
                 dict(latest=False, pageId='10', version='1')]
    monkeypatch.setattr(comparison.ConfigurationService, 'list_pages', lambda self: [])
    monkeypatch.setattr(comparison.RevisionService, 'get_page_revisions', lambda self, page: revisions)
    fetched = []

    async def fetch_page(self, page_id):
        fetched.append(page_id)
        cells = ['1', '', 'Activity', '', '', page_id, '', '', '']
        row = ''.join(f'<td>{value}</td>' for value in cells)
        return f'<table class="qms-structure-table"><tbody><tr>{row}</tr></tbody></table>'

    monkeypatch.setattr(ProcessPageContentService, 'fetch_process_page_html', fetch_page)

    def request(**overrides):
        payload = dict(method_page_id='30', method_name='Test method', published_page_id='20',
                       published_version='2', outdated_page_id='10', outdated_version='1')
        response = TestClient(app).post('/api/v1/procman/comparison/workflow', json=payload | overrides)
        response.raise_for_status()
        return [json.loads(line) for line in response.iter_lines()]

    return request, fetched


def test_automatic_workbook(workflow, monkeypatch):
    request, fetched = workflow
    paths = []
    generate = report_service.ProcessComparisonReportService.generate_report

    def record_report(*args, **kwargs):
        paths.append(Path(generate(*args, **kwargs)))
        return paths[-1]

    monkeypatch.setattr(report_service.ProcessComparisonReportService, 'generate_report', record_report)
    events = request()
    assert fetched == ['20', '10']
    assert [item['stage'] for item in events if 'stage' in item] == [
        'Fetching Process Compass content', 'Generating XML internally', 'Comparing versions', 'Generating the report']
    assert events[-1] == {'ready': True}
    assert len(paths) == 1 and not paths[0].parent.exists()
    data = b''.join(base64.b64decode(item['data']) for item in events if 'data' in item)
    workbook = load_workbook(BytesIO(data))
    assert workbook.sheetnames == ['Info-Summary', 'CompReport']
    assert workbook['Info-Summary']['B2'].value == 'Test method'
    workbook.close()


def test_workflow_uses_existing_configuration(workflow, monkeypatch):
    request, _ = workflow
    configured = dict(page_id='30', published_page_id='30', revisions=[dict(revision='1', revision_page_id='10')])
    monkeypatch.setattr(comparison.ConfigurationService, 'list_pages', lambda self: [configured])
    monkeypatch.setattr(comparison.RevisionService, 'get_page_revisions', lambda *args: pytest.fail('unexpected live lookup'))
    assert request(published_page_id='30', published_version='Published')[-1] == {'ready': True}


@pytest.mark.parametrize(('failure', 'stage'), [
    ('api', 'Fetching Process Compass content'), ('stale', 'Generating XML internally'),
    ('xml', 'Generating XML internally'), ('comparison', 'Comparing versions'), ('report', 'Generating the report'),
])
def test_workflow_failure_stops_pipeline(workflow, monkeypatch, failure, stage):
    request, _ = workflow

    def fail(*args, **kwargs):
        raise ValueError('Test failure')

    targets = {
        'api': (comparison.RevisionService, 'get_page_revisions'),
        'xml': (comparison.RevisionXmlGenerationService, 'generate_revision_xml'),
        'comparison': (ProcessPageContentService, 'parse_process_table'),
        'report': (report_service.ProcessComparisonReportService, 'generate_report'),
    }
    if failure in targets:
        monkeypatch.setattr(*targets[failure], fail)
    events = request(**({'published_version': 'missing'} if failure == 'stale' else {}))
    assert events[-2] == {'stage': stage}
    assert events[-1]['error'].startswith(stage)
    assert not any('ready' in item or 'data' in item for item in events)