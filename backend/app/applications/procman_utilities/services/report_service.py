
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin
import re

from app.core.temp_storage import get_temp_download_dir
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.comments import Comment


class ProcessComparisonReportService:
    """Generates Excel reports matching the original Process Compass report."""

    GREEN = "C6E0B4"
    RED = "F8CBAD"
    BLUE = "8DB4E2"
    LIGHT_BLUE = "92CDDC"

    RASIC_ROLES = [
        "Responsible",
        "Approval",
        "Support",
        "Informed",
        "Cooperation",
    ]

    DEPENDENCY_TYPES = [
        "Templates_Tools",
        "Method_mandatory",
        "Method_optional",
        "Instruction",
    ]

    @staticmethod
    def _display_text(value):
        if value is None:
            return ""

        return re.sub(
            r"&(?!amp;|lt;|gt;|quot;|apos;|#\d+;|#x[0-9a-fA-F]+;)",
            "&amp;",
            str(value),
        )

    @staticmethod
    def _make_hyperlink(href, base_url):
        if not href:
            return None

        href = str(href).strip()

        if not href or href == "IOwithoutLink":
            return None

        if href.startswith(("http://", "https://")):
            return href

        if not base_url:
            return None

        return urljoin(base_url.rstrip("/") + "/", href)

    @classmethod
    def _set_hyperlink(cls, cell, href, base_url):
        url = cls._make_hyperlink(href, base_url)

        if url:
            cell.hyperlink = url
            cell.font = Font(
                name=cell.font.name,
                size=cell.font.sz,
                bold=cell.font.bold,
                italic=cell.font.italic,
                color="0563C1",
                underline="single",
            )

    @staticmethod
    def _comment(cell, message):
        cell.comment = Comment(message, "Process Compass")

    @staticmethod
    def _grouped_item(item):
        if not isinstance(item, dict):
            return {
                "group": "",
                "name": str(item),
                "href": "",
            }

        return {
            "group": item.get(
                "group",
                item.get("Role", item.get("Dep_Type", "")),
            ),
            "name": item.get(
                "name",
                item.get("RoleName", item.get("Dep_Name", "")),
            ),
            "href": item.get(
                "href",
                item.get("RoleLink", item.get("Dep_Link", "")),
            ),
        }

    def _write_simple_items(
        self,
        sheet,
        column,
        start_row,
        published_items,
        change_result,
        base_url,
        published_version,
    ):
        """Write all published items and append deleted items."""

        published_items = (
            published_items
            if isinstance(published_items, dict)
            else {}
        )

        change_result = change_result or {}

        added = set(change_result.get("added", []))
        deleted = change_result.get("deleted", [])

        added_links = change_result.get("added_links", {})
        deleted_links = change_result.get("deleted_links", {})

        row = start_row

        for name, href in published_items.items():
            cell = sheet.cell(
                row,
                column,
                self._display_text(name),
            )

            if name in added:
                cell.fill = PatternFill(
                    "solid",
                    fgColor=self.GREEN,
                )
                self._comment(
                    cell,
                    f"Element Added to Latest Version {published_version}",
                )

            self._set_hyperlink(
                cell,
                added_links.get(name, href),
                base_url,
            )

            row += 1

        for name in deleted:
            cell = sheet.cell(
                row,
                column,
                self._display_text(name),
            )

            cell.fill = PatternFill(
                "solid",
                fgColor=self.RED,
            )

            self._comment(
                cell,
                f"Element Deleted from Latest Version {published_version}",
            )

            self._set_hyperlink(
                cell,
                deleted_links.get(name, ""),
                base_url,
            )

            row += 1

        return row - start_row

    def _write_grouped_items(
        self,
        sheet,
        column,
        start_row,
        published_items,
        change_result,
        group_order,
        base_url,
        published_version,
        include_empty_groups=False,
        blank_between_groups=False,
    ):
        """Write grouped entries while preserving empty group headings."""

        published_items = [
            self._grouped_item(item)
            for item in (published_items or [])
        ]

        change_result = change_result or {}

        added = [
            self._grouped_item(item)
            for item in change_result.get("added", [])
        ]

        deleted = [
            self._grouped_item(item)
            for item in change_result.get("deleted", [])
        ]

        added_ids = {
            (item["group"], item["name"])
            for item in added
            if item["name"]
        }

        published_groups = {
            item["group"]
            for item in published_items
            if item["group"]
        }

        deleted_groups = {
            item["group"]
            for item in deleted
            if item["group"]
        }

        present_groups = published_groups | deleted_groups

        if include_empty_groups:
            ordered_groups = list(group_order)

            extra_groups = sorted(
                present_groups - set(group_order)
            )

            ordered_groups.extend(extra_groups)

        else:
            ordered_groups = [
                group
                for group in group_order
                if group in present_groups
            ]

            ordered_groups.extend(
                sorted(present_groups - set(group_order))
            )

        row = start_row
        written_groups = 0

        for group in ordered_groups:

            group_items = [
                item
                for item in published_items
                if item["group"] == group and item["name"]
            ]

            deleted_group_items = [
                item
                for item in deleted
                if item["group"] == group and item["name"]
            ]

            if (
                not include_empty_groups
                and not group_items
                and not deleted_group_items
            ):
                continue

            if blank_between_groups and written_groups > 0:
                row += 1

            # Always write the group heading.
            heading_cell = sheet.cell(
                row,
                column,
                group,
            )

            heading_cell.font = Font(bold=True)
            row += 1

            # Write all entries from the published version.
            for item in group_items:
                cell = sheet.cell(
                    row,
                    column,
                    self._display_text(item["name"]),
                )

                if (group, item["name"]) in added_ids:
                    cell.fill = PatternFill(
                        "solid",
                        fgColor=self.GREEN,
                    )

                    self._comment(
                        cell,
                        f"Element Added to Latest Version {published_version}",
                    )

                self._set_hyperlink(
                    cell,
                    item["href"],
                    base_url,
                )

                row += 1

            # Append deleted entries in red.
            for item in deleted_group_items:
                cell = sheet.cell(
                    row,
                    column,
                    self._display_text(item["name"]),
                )

                cell.fill = PatternFill(
                    "solid",
                    fgColor=self.RED,
                )

                self._comment(
                    cell,
                    f"Element Deleted from Latest Version {published_version}",
                )

                self._set_hyperlink(
                    cell,
                    item["href"],
                    base_url,
                )

                row += 1

            written_groups += 1

        return row - start_row


    def _write_rasic_modified_csharp(
        self,
        sheet,
        column,
        start_row,
        published_items,
        outdated_items,
        change_result,
        base_url,
        published_version,
    ):
        """Match the original C# CompareRASIC row-index behaviour."""
        published_items = [
            self._grouped_item(item)
            for item in (published_items or [])
        ]
        outdated_items = [
            self._grouped_item(item)
            for item in (outdated_items or [])
        ]

        row = start_row

        for role in self.RASIC_ROLES:
            current = {
                item["name"]: item["href"]
                for item in published_items
                if item["group"] == role and item["name"]
            }
            previous = {
                item["name"]: item["href"]
                for item in outdated_items
                if item["group"] == role and item["name"]
            }

            # The C# code writes the heading at the current row.
            sheet.cell(row, column, role).font = Font(bold=True)

            # Dictionary.Keys.Union(): current keys, then old-only keys.
            names = list(current)
            names.extend(
                name for name in previous
                if name not in current
            )

            # C# advances once before the FIRST item only, not before
            # every item. It then advances once after each item.
            if names:
                row += 1

            for name in names:
                cell = sheet.cell(
                    row,
                    column,
                    self._display_text(name),
                )
                href = current.get(name, previous.get(name, ""))
                self._set_hyperlink(cell, href, base_url)

                if name not in current:
                    cell.fill = PatternFill("solid", fgColor=self.RED)
                    self._comment(
                        cell,
                        f"Element Deleted from Latest Version {published_version}",
                    )
                elif name not in previous:
                    cell.fill = PatternFill("solid", fgColor=self.GREEN)
                    self._comment(
                        cell,
                        f"Element Added to Latest Version {published_version}",
                    )

                row += 1

            # Deliberately no extra row increment for an empty RASIC role.
            # The next heading can overwrite an empty role heading, as in C#.

        return row - start_row

    def _write_dependencies_modified_csharp(
        self,
        sheet,
        column,
        start_row,
        published_items,
        outdated_items,
        change_result,
        base_url,
        published_version,
    ):
        """Match the original C# CompareDependencies row-index behaviour."""
        published_items = [
            self._grouped_item(item)
            for item in (published_items or [])
        ]
        outdated_items = [
            self._grouped_item(item)
            for item in (outdated_items or [])
        ]

        row = start_row

        for dep_type in self.DEPENDENCY_TYPES:
            current = {
                item["name"]: item["href"]
                for item in published_items
                if item["group"] == dep_type and item["name"]
            }
            previous = {
                item["name"]: item["href"]
                for item in outdated_items
                if item["group"] == dep_type and item["name"]
            }

            sheet.cell(row, column, dep_type).font = Font(bold=True)

            names = list(current)
            names.extend(
                name for name in previous
                if name not in current
            )

            # As in C#, advance once before the first item only.
            if names:
                row += 1

            for name in names:
                cell = sheet.cell(
                    row,
                    column,
                    self._display_text(name),
                )
                href = current.get(name, previous.get(name, ""))
                self._set_hyperlink(cell, href, base_url)

                if name not in current:
                    cell.fill = PatternFill("solid", fgColor=self.RED)
                    self._comment(
                        cell,
                        f"Element Deleted from Latest Version {published_version}",
                    )
                elif name not in previous:
                    cell.fill = PatternFill("solid", fgColor=self.GREEN)
                    self._comment(
                        cell,
                        f"Element Added to Latest Version {published_version}",
                    )

                row += 1

            # C# always advances after each dependency type, including empty ones.
            row += 1

        return row - start_row

    def _write_deleted_grouped_csharp(
        self, sheet, column, start_row, items, group_order,
        base_url, published_version,
    ):
        """Render deleted RASIC/dependency groups like the original C# methods."""
        normalized = [self._grouped_item(item) for item in (items or [])]
        row = start_row

        for group in group_order:
            group_items = [
                item for item in normalized
                if item["group"] == group and item["name"]
            ]

            heading = sheet.cell(row, column, group)
            heading.font = Font(bold=True)
            heading.fill = PatternFill("solid", fgColor=self.RED)
            self._comment(
                heading,
                f"Element Deleted from Latest Version {published_version}",
            )

            if group_items:
                row += 1

                for item in group_items:
                    cell = sheet.cell(
                        row, column, self._display_text(item["name"])
                    )
                    cell.fill = PatternFill("solid", fgColor=self.RED)
                    self._comment(
                        cell,
                        f"Element Deleted from Latest Version {published_version}",
                    )
                    self._set_hyperlink(cell, item["href"], base_url)

                    # The C# implementation inserts an extra row between
                    # entries when a group contains more than one item.
                    if len(group_items) > 1:
                        row += 1

            # C# advances once after every group, even an empty group.
            row += 1

        return row - start_row

    def generate_report(
        self,
        comparison_result: dict,
        method_name: str = "",
        published_version: str = "",
        outdated_version: str = "",
        confluence_base_url: str = "",
        output_dir: Path | None = None,
    ) -> str:

        workbook = Workbook()

        info_sheet = workbook.active
        info_sheet.title = "Info-Summary"

        report_sheet = workbook.create_sheet("CompReport")

        summary = comparison_result.get("summary", {})
        activities = comparison_result.get("activities", [])

        # --------------------------------------------------
        # Info-Summary
        # --------------------------------------------------

        info_sheet["A1"] = "Method Comparison Remarks"
        info_sheet["A2"] = "Method Name"
        info_sheet["B2"] = method_name

        info_sheet["A3"] = "Versions Compared"
        info_sheet["B3"] = (
            f"{published_version} and {outdated_version}"
        )

        info_sheet["A4"] = "Color Coding"
        info_sheet["B4"] = "Modified/New"
        info_sheet["B5"] = "Deleted"

        info_sheet["B4"].fill = PatternFill(
            "solid",
            fgColor=self.GREEN,
        )

        info_sheet["B5"].fill = PatternFill(
            "solid",
            fgColor=self.RED,
        )

        info_sheet["A8"] = "Comparison Summary"

        summary_labels = [
            ("Activities Added", "activities_added"),
            ("Activities Deleted", "activities_deleted"),
            ("Activities Modified", "activities_modified"),
            ("Inputs Added", "inputs_added"),
            ("Inputs Deleted", "inputs_deleted"),
            ("Outputs Added", "outputs_added"),
            ("Outputs Deleted", "outputs_deleted"),
            ("Rasic Roles Added", "rasic_added"),
            ("Rasic Roles Deleted", "rasic_deleted"),
            ("Guidance elements Added", "dependencies_added"),
            ("Guidance elements Deleted", "dependencies_deleted"),
        ]

        for row, (label, key) in enumerate(
            summary_labels,
            start=8,
        ):
            info_sheet.cell(row, 2, label)
            info_sheet.cell(
                row,
                3,
                summary.get(key, 0),
            )

        activity_labels = [
            ("Inputs Added", "inputs_added", "added"),
            ("Inputs Deleted", "inputs_added", "deleted"),
            ("Outputs Added", "outputs_added", "added"),
            ("Outputs Deleted", "outputs_added", "deleted"),
            ("Rasic Roles Added", "rasic_added", "added"),
            ("Rasic Roles Deleted", "rasic_added", "deleted"),
            ("Guidance elements Added", "dependencies_added", "added"),
            ("Guidance elements Deleted", "dependencies_added", "deleted"),
        ]

        info_sheet["A20"] = "Comparison Summary Activity Wise"
        info_sheet["B20"] = (
            "Activity-wise summary considers only modified activities"
        )

        info_row = 21

        for activity in activities:
            if activity.get("status") != "modified" or not activity.get("changes"):
                continue

            changes = activity.get("changes", {})
            published = activity.get("published") or {}

            info_sheet.cell(
                info_row,
                1,
                self._display_text(
                    published.get("Title", "")
                ),
            )

            info_sheet.cell(
                info_row,
                1,
            ).fill = PatternFill(
                "solid",
                fgColor=self.LIGHT_BLUE,
            )

            info_row += 1

            for label, key, change_type in activity_labels:
                result = changes.get(key, {})
                count = len(result.get(change_type, []))

                info_sheet.cell(
                    info_row,
                    2,
                    label,
                )

                info_sheet.cell(
                    info_row,
                    3,
                    count,
                )

                info_row += 1

            info_row += 1

        # --------------------------------------------------
        # CompReport
        # --------------------------------------------------

        headers = [
            "Sl No",
            "Activity",
            "Successor",
            "Inputs",
            "Outputs",
            "RASIC",
            "Dependencies",
        ]

        report_sheet.append(headers)

        for cell in report_sheet[1]:
            cell.font = Font(
                bold=True,
                size=14,
            )

            cell.alignment = Alignment(
                horizontal="center",
                vertical="center",
                wrap_text=True,
            )

        report_sheet["G1"].font = Font(
            bold=True,
            size=16,
        )

        report_sheet.row_dimensions[1].height = 30

        thin_side = Side(style="thin")
        medium_side = Side(style="medium")

        for index, activity in enumerate(
            activities,
            start=1,
        ):
            status = activity.get("status", "")

            if status not in (
                "added",
                "modified",
                "deleted",
            ):
                continue

            published = activity.get("published") or {}
            outdated = activity.get("outdated") or {}
            changes = activity.get("changes") or {}

            current = (
                outdated
                if status == "deleted"
                else published
            )

            start_row = report_sheet.max_row + 1

            report_sheet.cell(
                start_row,
                1,
                current.get("Nr", index),
            )

            report_sheet.cell(
                start_row,
                2,
                self._display_text(
                    current.get("Title", "")
                ),
            )

            new_next = published.get("Next", "")
            old_next = outdated.get("Next", "")

            successor_rows = 1

            successor_cell = report_sheet.cell(
                start_row,
                3,
                self._display_text(
                    old_next
                    if status == "deleted"
                    else new_next
                ),
            )

            if (
                status == "modified"
                and old_next != new_next
            ):
                successor_cell.fill = PatternFill(
                    "solid",
                    fgColor=self.GREEN,
                )

                previous_cell = report_sheet.cell(
                    start_row + 1,
                    3,
                    self._display_text(old_next),
                )

                previous_cell.fill = PatternFill(
                    "solid",
                    fgColor=self.RED,
                )

                self._comment(
                    previous_cell,
                    f"Previous value: {old_next}",
                )

                successor_rows = 2

            activity_color = (
                self.GREEN
                if status == "added"
                else self.RED
                if status == "deleted"
                else None
            )

            if activity_color:
                for column in range(1, 4):
                    report_sheet.cell(
                        start_row,
                        column,
                    ).fill = PatternFill(
                        "solid",
                        fgColor=activity_color,
                    )

            if status == "modified":
                if (
                    outdated.get("Title", "")
                    != published.get("Title", "")
                ):
                    title_cell = report_sheet.cell(
                        start_row,
                        2,
                    )

                    title_cell.fill = PatternFill(
                        "solid",
                        fgColor=self.GREEN,
                    )

                    self._comment(
                        title_cell,
                        f"Previous value: {outdated.get('Title', '')}",
                    )

                input_changes = changes.get(
                    "inputs_added",
                    {},
                )

                output_changes = changes.get(
                    "outputs_added",
                    {},
                )

                rasic_changes = changes.get(
                    "rasic_added",
                    {},
                )

                dependency_changes = changes.get(
                    "dependencies_added",
                    {},
                )

            elif status == "added":
                input_changes = {
                    "added": list(
                        published.get("InputDic", {}).keys()
                    ),
                    "deleted": [],
                    "added_links": published.get(
                        "InputDic",
                        {},
                    ),
                }

                output_changes = {
                    "added": list(
                        published.get("OutputDic", {}).keys()
                    ),
                    "deleted": [],
                    "added_links": published.get(
                        "OutputDic",
                        {},
                    ),
                }

                rasic_changes = {
                    "added": published.get("RASIC", []),
                    "deleted": [],
                }

                dependency_changes = {
                    "added": published.get(
                        "Dependencies",
                        [],
                    ),
                    "deleted": [],
                }

            else:
                input_changes = {
                    "added": [],
                    "deleted": list(
                        outdated.get("InputDic", {}).keys()
                    ),
                    "deleted_links": outdated.get(
                        "InputDic",
                        {},
                    ),
                }

                output_changes = {
                    "added": [],
                    "deleted": list(
                        outdated.get("OutputDic", {}).keys()
                    ),
                    "deleted_links": outdated.get(
                        "OutputDic",
                        {},
                    ),
                }

                rasic_changes = {
                    "added": [],
                    "deleted": outdated.get("RASIC", []),
                }

                dependency_changes = {
                    "added": [],
                    "deleted": outdated.get(
                        "Dependencies",
                        [],
                    ),
                }

            inputs = (
                published.get("InputDic", {})
                if status != "deleted"
                else {}
            )

            outputs = (
                published.get("OutputDic", {})
                if status != "deleted"
                else {}
            )

            rasic = (
                published.get("RASIC", [])
                if status != "deleted"
                else []
            )

            dependencies = (
                published.get("Dependencies", [])
                if status != "deleted"
                else []
            )

            max_height = successor_rows

            max_height = max(
                max_height,
                self._write_simple_items(
                    report_sheet,
                    4,
                    start_row,
                    inputs,
                    input_changes,
                    confluence_base_url,
                    published_version,
                ),
            )

            max_height = max(
                max_height,
                self._write_simple_items(
                    report_sheet,
                    5,
                    start_row,
                    outputs,
                    output_changes,
                    confluence_base_url,
                    published_version,
                ),
            )

            if status == "modified":
                # Match the original C# methods and reserved row heights.
                self._write_rasic_modified_csharp(
                    report_sheet, 6, start_row, rasic,
                    outdated.get("RASIC", []), rasic_changes,
                    confluence_base_url, published_version,
                )
                self._write_dependencies_modified_csharp(
                    report_sheet, 7, start_row, dependencies,
                    outdated.get("Dependencies", []), dependency_changes,
                    confluence_base_url, published_version,
                )
                max_height = max(
                    max_height,
                    max(len(rasic), len(outdated.get("RASIC", []))) + 9,
                    max(len(dependencies), len(outdated.get("Dependencies", []))) + 8,
                )
            elif status == "deleted":
                # The original C# deleted-activity path writes every enum
                # heading, including empty groups, and colors headings/items red.
                rasic_rows = self._write_deleted_grouped_csharp(
                    report_sheet, 6, start_row,
                    outdated.get("RASIC", []), self.RASIC_ROLES,
                    confluence_base_url, published_version,
                )
                dependency_rows = self._write_deleted_grouped_csharp(
                    report_sheet, 7, start_row,
                    outdated.get("Dependencies", []), self.DEPENDENCY_TYPES,
                    confluence_base_url, published_version,
                )
                max_height = max(
                    max_height,
                    len(outdated.get("InputDic", {})),
                    len(outdated.get("OutputDic", {})),
                    len(outdated.get("RASIC", [])) + 5,
                    len(outdated.get("Dependencies", [])) + 4,
                    rasic_rows,
                    dependency_rows,
                )
            else:
                max_height = max(
                    max_height,
                    self._write_grouped_items(
                        report_sheet, 6, start_row, rasic, rasic_changes,
                        self.RASIC_ROLES, confluence_base_url, published_version,
                        include_empty_groups=False, blank_between_groups=False,
                    ),
                )
                max_height = max(
                    max_height,
                    self._write_grouped_items(
                        report_sheet, 7, start_row, dependencies, dependency_changes,
                        self.DEPENDENCY_TYPES, confluence_base_url, published_version,
                        include_empty_groups=True, blank_between_groups=True,
                    ),
                )

            last_row = start_row + max_height - 1

            for cell in report_sheet[last_row]:
                cell.border = Border(
                    bottom=medium_side,
                )

            report_sheet.row_dimensions[last_row].height = 22

            # Blank separator between activities.
            report_sheet.cell(last_row + 1, 1)

        # --------------------------------------------------
        # Formatting
        # --------------------------------------------------

        for cell in ["A1", "A8", "A20"]:
            info_sheet[cell].fill = PatternFill(
                "solid",
                fgColor=self.BLUE,
            )

        for cell in [
            "A1",
            "A2",
            "A3",
            "A4",
            "A8",
            "A20",
            "B20",
        ]:
            info_sheet[cell].font = Font(bold=True)

        info_sheet.column_dimensions["A"].width = 35
        info_sheet.column_dimensions["B"].width = 65
        info_sheet.column_dimensions["C"].width = 9

        for column, width in {
            "A": 12,
            "B": 30,
            "C": 30,
            "D": 35,
            "E": 35,
            "F": 35,
            "G": 35,
        }.items():
            report_sheet.column_dimensions[column].width = width

        for sheet in [
            info_sheet,
            report_sheet,
        ]:
            for row in sheet.iter_rows():
                for cell in row:
                    cell.alignment = Alignment(
                        vertical="top",
                        wrap_text=True,
                    )

                    cell.border = Border(
                        left=thin_side,
                        right=thin_side,
                        top=thin_side,
                        bottom=thin_side,
                    )

        report_sheet.freeze_panes = "C2"

        # --------------------------------------------------
        # Save
        # --------------------------------------------------

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")

        safe_method = "".join(
            char
            if char.isalnum() or char in "_-"
            else "_"
            for char in method_name
        )

        filename = (
            f"CompReport_{safe_method}_{timestamp}.xlsx"
        )

        output_path = (output_dir or get_temp_download_dir()) / filename

        workbook.save(output_path)
        workbook.close()

        return str(output_path)
