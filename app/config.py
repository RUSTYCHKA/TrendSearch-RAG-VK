import os
from dotenv import load_dotenv

load_dotenv()

VK_TOKEN = os.getenv("VK_TOKEN", "")
DATABASE_URL = os.getenv("DATABASE_URL", "")

RAW_DATA_DIR = "data/raw"