import os
from utils.utils import get_env

os.makedirs(get_env("DATA_DIR"), exist_ok=True)
