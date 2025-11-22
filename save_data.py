import logging
from datetime import datetime

from pymongo import MongoClient
from telethon import TelegramClient

from db_data import get_data
from secret import *
from log import add_log

# --- Configure logger ---
logging.basicConfig(
    filename="scraper.log",  # log file name
    level=logging.INFO,  # log level
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding="utf-8",  # ensure Persian text logs correctly
)
logger = logging.getLogger(__name__)
# --- MongoDB setup ---
mongo_client = MongoClient("mongodb://localhost:27017/")
db = mongo_client["bazarbin_data"]
collection = db["prices"]

# --- Telethon client ---
if PROXY_SERVER and PROXY_PORT:
    client = TelegramClient(
        "scraper", API_ID, API_HASH, proxy=("socks5", PROXY_SERVER, int(PROXY_PORT))
    )
else:
    client = TelegramClient("scraper", API_ID, API_HASH)


async def main():
    await client.start()

    # Get channel entity
    channel = await client.get_entity(CHANNEL_USERNAME)  # or channel ID

    async for message in client.iter_messages(channel, limit=None):
        msg = message.text
        if not msg:
            t = f"Ignored - {message.id}"
            logger.info(t)
            add_log(t)
            continue
        if msg.startswith("دلار (USD)") or msg.startswith("USDT (تتر)"):
            data_dict = get_data(msg)
            dt = datetime.fromisoformat(str(message.date))
            start = dt.replace(second=0, microsecond=0)
            end = start.replace(second=59, microsecond=999999)

            # Query range: match any timestamp in that minute
            query = {"timestamp": {"$gte": start, "$lte": end}}

            # Try to update existing document
            update_result = collection.update_one(
                query, {"$set": {"message_id": f"{message.id}"}}
            )

            # If no document matched, insert a new one
            if update_result.matched_count == 0:
                data_dict["message_id"] = f"{message.id}"
                data_dict["timestamp"] = dt
                result = collection.insert_one(data_dict)
                logger.info(f"{message.id} - status={result.acknowledged}")
                print(f"{message.id} - status={result.acknowledged}")
            else:
                logger.info(f"{message.id} - result={update_result.modified_count}")
                print(f"{message.id} - result={update_result.modified_count}")
        else:
            t = f"Ignored - {message.id}"
            logger.info(t)
            add_log(t)

    print("All messages saved to MongoDB.")


with client:
    client.loop.run_until_complete(main())
