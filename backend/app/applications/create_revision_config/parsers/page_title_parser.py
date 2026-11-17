
import re

UUID_PATTERN = re.compile(
    r"[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-"
    r"[a-fA-F0-9]{4}-[a-fA-F0-9]{12}_"
)


def normalize_page_title(title: str) -> str:
    if not title:
        return ""

    match = UUID_PATTERN.search(title)

    if match:
        return title.replace(match.group(0), "", 1)

    return title
