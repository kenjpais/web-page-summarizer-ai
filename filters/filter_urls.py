from pathlib import Path
from utils.file_utils import MultiFileManager
from config.settings import get_settings
from utils.logging_config import get_logger

logger = get_logger(__name__)

settings = get_settings()
data_dir = Path(settings.directories.data_dir)


def filter_urls():
    logger.info("[*] Filtering relevant URLs...")

    fm = MultiFileManager()
    servers = settings.processing.get_sources_dict()
    with fm:
        with open(data_dir / "urls.txt") as f:
            for url in f:
                url = url.strip()
                for src, server in servers.items():
                    if server in url:
                        fm.write(
                            data_dir / f"{src.lower()}_urls.txt",
                            url + "\n",
                        )
