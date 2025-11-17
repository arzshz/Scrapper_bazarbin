from telethon import TelegramClient
from telethon.tl.types import PeerChannel
from pymongo import MongoClient
import asyncio

from get_prices import get_data
from secret import *

# --- MongoDB setup ---
mongo_client = MongoClient("mongodb://localhost:27017/")
db = mongo_client["bazarbin_data"]
collection = db["message_dates"]

# --- Telethon client ---
client = TelegramClient('scraper', API_ID, API_HASH, proxy=("socks5", PROXY_SERVER, int(PROXY_PORT)))

async def main():
    await client.start()

    # Get channel entity
    channel = await client.get_entity(CHANNEL_USERNAME)  # or channel ID

    async for message in client.iter_messages(channel, limit=None):
        data_dict = get_data(message.text)
        print(message.text)
        print(message.id)
        print(message.date)
        txt = message.text
        txt_list = txt.split("\n")
        final_text = ""
        # for t in txt_list:
        #     if
        break
        # doc = {
        #     "message_id": message.id,
        #     "date": message.date.isoformat() if message.date else None,
        # }
        #
        # try:
        #     collection.insert_one(doc)
        # except Exception as e:
        #     print(f"Error inserting message {message.id}: {e}")

    print("All messages saved to MongoDB.")

with client:
    client.loop.run_until_complete(main())


a = """دلار (USD)
فردایی [سبزه](https://t.me/tahran_sabza/681057) و [تهران](https://t.me/dollar_tehran3bze/696182): 112,000 | 111,950
نقدی [سبزه](https://t.me/tahran_sabza/681014) و [تهران](https://t.me/dollar_tehran3bze/696139): 111,900 | 111,850
[بن‌بست](https://www.bonbast.com/): 111,550 | 111,450
[سایت tgju (آزاد)](https://www.tgju.org/قیمت-دلار): 111,980


USDT (تتر)
[Nobitex_150](https://nobitex.ir/panel/exchange/usdt-irt/): 112,905 | 112,895 ❇️
[Nobitex_5000](https://nobitex.ir/panel/exchange/usdt-irt/): 112,905 | 112,836
[Wallex](https://wallex.ir/): 112,740 | 112,739
[Bitpin](https://bitpin.ir/): ✴️ 112,685 | 112,685
[Ramzinex](https://ramzinex.com/): 112,850 | 112,770


طلا (GOLD) (بر اساس tala.ir)
[اونس طلا](https://www.tala.ir/gold-price): 4,082$
[مظنه بازار تهران](https://www.tala.ir/gold-price): 47,887,000
[طلای 18 عیار](https://www.tala.ir/gold-price): 11,054,700
[سکه قدیم](https://www.tala.ir/gold-price): 109,500,000
[سکه جدید](https://www.tala.ir/gold-price): 115,200,000
[ربع سکه](https://www.tala.ir/gold-price): 33,800,000


Ethereum Gas
[Etherscan](https://etherscan.io/gastracker): 0.105 | 0.105 | 0.115


رمز ارز (Cryptocurrency)
[بیت‌کوین](https://www.binance.com/en/trade/BTCUSDT): 95,620$
[اتر](https://www.binance.com/en/trade/ETHUSDT): 3,173$
[بی‌ان‌بی (BNB)](https://www.binance.com/en/trade/BNBUSDT): 938$

1404/08/25   18:15


🆔 @bazar_bin"""

b = """dollar (USD)
tom [sbz](https://t.me/the_channel_1/681057) و [th](https://t.me/the_channel_2/696182): 112,000 | 111,950
ngh [sbz](https://t.me/the_channel_1/681014) و [th](https://t.me/the_channel_2/696139): 111,900 | 111,850
[alley](https://www.alley.com/): 111,550 | 111,450
[the site (free)](https://www.site.org/price): 111,980


USDT (the USDT)
[exch_1](https://exch_1.org/panel/exchange/usdt-eth/): 112,905 | 112,895 ❇️
[exch_2](https://exch_1.org/panel/exchange/usdt-eth/): 112,905 | 112,836
[exch_3](https://exch_3.org/): 112,740 | 112,739
[exch_4](https://exch_4.org/): ✴️ 112,685 | 112,685
[exch_5](https://exch_5.org/): 112,850 | 112,770


the gold (GOLD) (as gold.org)
[part1](https://www.gold.org/gold-price): 4,082$
[part2](https://www.gold.org/gold-price): 47,887,000
[part3](https://www.gold.org/gold-price): 11,054,700
[part4](https://www.gold.org/gold-price): 109,500,000
[part5](https://www.gold.org/gold-price): 115,200,000
[part6](https://www.gold.org/gold-price): 33,800,000


Ethereum Gas
[Etherscan](https://etherscan.io/gastracker): 0.105 | 0.105 | 0.115


coins (Cryptocurrency)
[btc](https://www.binance.com/en/trade/BTCUSDT): 95,620$
[eth](https://www.binance.com/en/trade/ETHUSDT): 3,173$
[BNB](https://www.binance.com/en/trade/BNBUSDT): 938$

2024/08/25   18:15


🆔 @my_channel"""