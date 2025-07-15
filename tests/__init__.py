import os
from pathlib import Path
from utils.utils import get_env

Path(get_env("DATA_DIR")).mkdir(exist_ok=True)
