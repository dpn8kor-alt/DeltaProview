
import json
from bs4 import BeautifulSoup


def parse_revision_history_page(response_content: str) -> list[dict]:
    """Parse revision history from raw JSON or HTML containing a <pre> element."""

    content = response_content.strip()

    # Direct HTTP response: raw JSON
    if content.startswith("["):
        payload = json.loads(content)

    # Browser response: HTML containing JSON inside <pre>
    else:
        soup = BeautifulSoup(content, "lxml")
        node = soup.find("pre")

        if node is None:
            raise ValueError(
                "Revision-history response did not contain JSON or an expected <pre> element."
            )

        payload = json.loads(node.get_text())

    if not isinstance(payload, list):
        raise ValueError("Expected revision-history JSON array.")

    return payload
