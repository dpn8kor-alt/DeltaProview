from pathlib import Path

from openpyxl import load_workbook
import pytest

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