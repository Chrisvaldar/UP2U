import os
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"

handlers = [
    logging.StreamHandler(),
]
if DEBUG:
    LOG_DIR.mkdir(exist_ok=True)
    handlers.append(logging.FileHandler(LOG_DIR / "app.log", encoding="utf-8"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    handlers=handlers,
)
logger = logging.getLogger(__name__)
