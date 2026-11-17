from pathlib import Path
from tempfile import gettempdir


def get_temp_download_dir() -> Path:
    directory = Path(gettempdir()) / "ProcessCompass"
    directory.mkdir(parents=True, exist_ok=True)
    return directory