import os

from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TOKEN_LOGGING = os.getenv("TOKEN_LOGGING")
LOG_CHANNEL_ID = os.getenv("LOG_CHANNEL_ID")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")  # Channel username (without @)
CHANNEL_JSON = os.getenv("CHANNEL_JSON")
PROXY_SERVER = os.getenv("PROXY_SERVER")
PROXY_PORT = os.getenv("PROXY_PORT")
