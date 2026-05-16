import os
import logging
from dotenv import load_dotenv
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

# Load .env file
load_dotenv()

logger = logging.getLogger(__name__)

# Server Settings
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", 8080))

# Database Settings
DB_PATH = os.getenv("DB_PATH", "srbase.db")

# Timezone Settings
TZ_NAME = os.getenv("APP_TIMEZONE", "UTC")
try:
    APP_TZ = ZoneInfo(TZ_NAME)
except ZoneInfoNotFoundError:
    logger.error("Invalid APP_TIMEZONE: %s. Falling back to UTC.", TZ_NAME)
    APP_TZ = ZoneInfo("UTC")

# Telegram Settings
TG_TOKEN = os.getenv("TG_TOKEN")
TG_MAPPING = os.getenv("TG_MAPPING", "")
