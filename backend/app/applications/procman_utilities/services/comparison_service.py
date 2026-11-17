
class ProcessComparisonService:
    """Compares published and outdated Process Compass activities."""

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

    def compare(self, published: list[dict], outdated: list[dict]) -> dict:
        published = [self._normalize(row) for row in published]
        outdated = [self._normalize(row) for row in outdated]

        activities = []
        matched_outdated = set()

        summary = {
            "activities_added": 0,
            "activities_deleted": 0,
            "activities_modified": 0,
            "inputs_added": 0,
            "inputs_deleted": 0,
            "outputs_added": 0,
            "outputs_deleted": 0,
            "rasic_added": 0,
            "rasic_deleted": 0,
            "dependencies_added": 0,
            "dependencies_deleted": 0,
        }

        # Match published activities with outdated activities by exact title.
        for current in published:
            title = str(current.get("Title", "")).strip()

            previous_index = next(
                (
                    index
                    for index, row in enumerate(outdated)
                    if index not in matched_outdated
                    and str(row.get("Title", "")).strip() == title
                ),
                None,
            )

            if previous_index is None:
                activities.append({
                    "status": "added",
                    "published": current,
                    "outdated": None,
                    "changes": {},
                })

                summary["activities_added"] += 1
                continue

            matched_outdated.add(previous_index)
            previous = outdated[previous_index]

            changes = self._compare_activity(current, previous)

            activities.append({
                "status": "modified",
                "published": current,
                "outdated": previous,
                "changes": changes,
            })

            if changes:
                summary["activities_modified"] += 1

            # Update item-level summary counts.
            for key, value in changes.items():
                if not isinstance(value, dict):
                    continue

                if key in summary:
                    summary[key] += len(value.get("added", []))

                deleted_key = key.replace("_added", "_deleted")

                if deleted_key in summary:
                    summary[deleted_key] += len(value.get("deleted", []))

        # Any unmatched outdated activity is deleted.
        for index, previous in enumerate(outdated):
            if index in matched_outdated:
                continue

            activities.append({
                "status": "deleted",
                "published": None,
                "outdated": previous,
                "changes": {},
            })

            summary["activities_deleted"] += 1

        # Sort activities by their process-flow number.
        # Published activity comes before deleted activity for equal numbers.
        def activity_sort_key(item):
            activity = item.get("published") or item.get("outdated") or {}
            nr = activity.get("Nr", "")

            try:
                number = float(nr)
            except (TypeError, ValueError):
                number = float("inf")

            priority = 1 if item.get("status") == "deleted" else 0

            return number, priority

        activities.sort(key=activity_sort_key)

        return {
            "activities": activities,
            "summary": summary,
        }

    @staticmethod
    def _normalize(row: dict) -> dict:
        """Accept original C# field names and parsed Python fields."""

        return {
            "Nr": row.get("Nr", row.get("step", "")),
            "Title": row.get("Title", row.get("title", "")),
            "Next": row.get("Next", row.get("next", "")),
            "InputDic": row.get("InputDic", row.get("input", {})) or {},
            "OutputDic": row.get("OutputDic", row.get("output", {})) or {},
            "RASIC": row.get("RASIC", row.get("rasic", [])) or [],
            "Dependencies": row.get(
                "Dependencies", row.get("dependencies", [])
            ) or [],
        }

    def _compare_activity(self, current: dict, previous: dict) -> dict:
        changes = {}

        # Compare activity title and successor.
        for field in ("Title", "Next"):
            new_value = str(current.get(field, "") or "")
            old_value = str(previous.get(field, "") or "")

            if new_value != old_value:
                changes[field] = {
                    "published": new_value,
                    "outdated": old_value,
                }

        # Compare Inputs and Outputs by item names.
        for field, added_key in (
            ("InputDic", "inputs_added"),
            ("OutputDic", "outputs_added"),
        ):
            result = self._compare_named_items(
                current.get(field, {}),
                previous.get(field, {}),
            )

            if result["added"] or result["deleted"]:
                changes[added_key] = result

        # Compare RASIC by role and role name.
        rasic_result = self._compare_grouped_items(
            current.get("RASIC", []),
            previous.get("RASIC", []),
            "Role",
            "RoleName",
            self.RASIC_ROLES,
        )

        if rasic_result["added"] or rasic_result["deleted"]:
            changes["rasic_added"] = rasic_result

        # Compare Dependencies by type and name.
        dependency_result = self._compare_grouped_items(
            current.get("Dependencies", []),
            previous.get("Dependencies", []),
            "Dep_Type",
            "Dep_Name",
            self.DEPENDENCY_TYPES,
        )

        if dependency_result["added"] or dependency_result["deleted"]:
            changes["dependencies_added"] = dependency_result

        return changes

    @staticmethod
    def _compare_named_items(current: dict, previous: dict) -> dict:
        current = current if isinstance(current, dict) else {}
        previous = previous if isinstance(previous, dict) else {}

        current_names = set(current.keys())
        previous_names = set(previous.keys())

        added = sorted(current_names - previous_names)
        deleted = sorted(previous_names - current_names)

        return {
            "added": added,
            "deleted": deleted,
            "added_links": {
                name: current.get(name, "")
                for name in added
            },
            "deleted_links": {
                name: previous.get(name, "")
                for name in deleted
            },
        }

    @staticmethod
    def _to_grouped_dict(items, group_field, name_field):
        grouped = {}

        if isinstance(items, dict):
            for group, values in items.items():
                if isinstance(values, dict):
                    grouped[group] = values
                elif isinstance(values, (list, tuple, set)):
                    grouped[group] = {
                        str(value): "" for value in values
                    }

            return grouped

        if not isinstance(items, list):
            return grouped

        for item in items:
            if not isinstance(item, dict):
                continue

            group = str(item.get(group_field, ""))
            name = str(item.get(name_field, item.get("text", "")))

            if group and name:
                grouped.setdefault(group, {})[name] = item.get(
                    "RoleLink",
                    item.get("Dep_Link", item.get("href", "")),
                )

        return grouped

    def _compare_grouped_items(
        self,
        current,
        previous,
        group_field,
        name_field,
        group_order,
    ):
        current_groups = self._to_grouped_dict(
            current, group_field, name_field
        )

        previous_groups = self._to_grouped_dict(
            previous, group_field, name_field
        )

        added = []
        deleted = []

        for group in group_order:
            current_items = current_groups.get(group, {})
            previous_items = previous_groups.get(group, {})

            current_names = set(current_items.keys())
            previous_names = set(previous_items.keys())

            added.extend(
                {
                    "group": group,
                    "name": name,
                    "href": current_items.get(name, ""),
                }
                for name in sorted(current_names - previous_names)
            )

            deleted.extend(
                {
                    "group": group,
                    "name": name,
                    "href": previous_items.get(name, ""),
                }
                for name in sorted(previous_names - current_names)
            )

        return {
            "added": added,
            "deleted": deleted,
        }
