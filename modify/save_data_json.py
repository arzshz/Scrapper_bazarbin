import ast
import logging
from datetime import datetime

from pymongo import MongoClient
from telethon import TelegramClient

from db_data import to_int, get_data_dict
from log import add_log
from secret import *

usd_dict = {
    "صداقت": "sedaghat",
    "سبزه": "sabze",
    "تهران": "tehran",
    "بن بست": "bonbast",
    "بن\u200cبست": "bonbast",
}
gold_dict = {
    "اونس طلا": "ounce",
    "مظنه بازار تهران": "tehran_market_price",
    "طلای 18 عیار": "18_karat_gold",
    "سکه قدیم": "old_coin",
    "سکه جدید": "new_coin",
}
coin_dict = {
    "بیت\u200cکوین": "btc",
    "اتر": "eth",
    "ماتیک": "pol",
    "فانتوم": "ftm",
    "مونرو": "xmr",
}

# --- Configure logger ---
logging.basicConfig(
    filename="../scraper.log",  # log file name
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
    channel = await client.get_entity(CHANNEL_JSON)  # or channel ID

    async for message in client.iter_messages(channel, limit=None):
        msg = message.text
        if not msg:
            t = f"Ignored - {message.id}"
            logger.info(t)
            add_log(t)
            continue
        if msg.startswith("{"):
            the_data = ast.literal_eval(msg)
            data_dict = get_json_data(the_data)
            dt = datetime.fromisoformat(str(message.date))
            start = dt.replace(second=0, microsecond=0)
            end = start.replace(second=59, microsecond=999999)

            # Query range: match any timestamp in that minute
            query = {"timestamp": {"$gte": start, "$lte": end}}

            existing_doc = collection.find_one(query)

            if not existing_doc:
                data_dict["timestamp"] = dt
                result = collection.insert_one(data_dict)
                logger.info(f"{message.id} - status={result.acknowledged}")
                print(f"{message.id} - status={result.acknowledged}")
            else:
                print("exists")
        else:
            t = f"Ignored - {message.id}"
            logger.info(t)
            add_log(t)

    print("All messages saved to MongoDB.")


def get_json_data(the_data):
    data_dict = get_data_dict()
    data_dict["crypto"] = {}
    for k, v in the_data.items():
        if k == "USD":
            for k1, v1 in v.items():
                buy, sell = to_int(v1["buy"]), to_int(v1["sell"])
                if "usd" not in data_dict["currency_rates"]:
                    data_dict["currency_rates"]["usd"] = {}
                data_dict["currency_rates"]["usd"].update(
                    {usd_dict[k1]: {"buy": buy, "sell": sell}}
                )
        elif k == "USDT":
            for k1, v1 in v.items():
                bid, ask = to_int(v1["buy"]), to_int(v1["sell"])
                if k1.lower() in data_dict["currency_rates"]["usdt"]:
                    data_dict["currency_rates"]["usdt"][k1.lower()] = {
                        "ask": ask,
                        "bid": bid,
                    }
        elif k == "GOLD":
            for k1, v1 in v.items():
                price = to_int(v1["price"].replace("$", ""))
                data_dict["gold_prices"]["tala.ir"].update(
                    {gold_dict[k1]: {"price": price}}
                )
        elif k == "Cryptocurrency":
            for k1, v1 in v.items():
                price = to_int(v1["price"])
                data_dict["crypto"].update({coin_dict[k1]: {"price": price}})
    return data_dict


with client:
    client.loop.run_until_complete(main())
