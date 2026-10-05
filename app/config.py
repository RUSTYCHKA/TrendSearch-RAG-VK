import os
from dotenv import load_dotenv

load_dotenv()

VK_TOKEN = os.getenv("VK_TOKEN", "")
RAW_DATA_DIR = "data/raw"