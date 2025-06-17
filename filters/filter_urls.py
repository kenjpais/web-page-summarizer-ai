import json
from utils.utils import get_env
from utils.file_utils import MultiFileManager


def filter_urls():
    print("\n[*] Filtering relevant URLs...")

    fm = MultiFileManager()
    sources = json.loads(get_env("SOURCES"))
    servers = {src: get_env(f"{src.upper()}_SERVER") for src in sources}
    data_dir = get_env("DATA_DIR")
    with fm:
        with open(f"{data_dir}/urls.txt") as f:
            for url in f:
                url = url.strip()
                for src, server in servers.items():
                    if server in url:
                        fm.write(f"{data_dir}/{src.lower()}_urls.txt", url + "\n")
