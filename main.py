from datetime import datetime as dt

import jdatetime
import pytz
import telebot
from telebot import types

from get_text_from_db import get_text
from log import add_log
from parsers import parse_date_and_time, tehran_tz
from secret import *

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

from datetime import timedelta, timezone
from pymongo import ASCENDING, MongoClient

mongo_client = MongoClient("mongodb://localhost:27017/")
db = mongo_client["bazarbin_data"]
collection = db["prices"]


def get_nearest_data(dt_object: dt):
    dt_object = dt_object.astimezone(timezone.utc)

    start = dt_object - timedelta(minutes=2, seconds=30)
    end = dt_object + timedelta(minutes=2, seconds=30)

    cursor = collection.find({"timestamp": {"$gte": start, "$lte": end}}).sort(
        "timestamp", ASCENDING
    )

    docs = list(cursor)
    if not docs:
        return None

    nearest_doc = min(
        docs,
        key=lambda doc: abs(doc["timestamp"].replace(tzinfo=timezone.utc) - dt_object),
    )
    return nearest_doc


def to_jalali(dt_object: dt) -> str:
    jalali_date = jdatetime.datetime.fromgregorian(datetime=dt_object)
    return jalali_date.strftime("%Y/%m/%d   %H:%M")


# ===== TELEGRAM BOT HANDLERS =====
@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
    welcome_text = """
*BazarBin Message Forwarder Bot*

Send me a date and I'll find the first message from the channel for that date!

🗓 *Supported date formats:*
- Jalali/Shamsi: 1403/02/15, 1403-02-15, 14030215
- Gregorian: 2024/05/05, 2024-05-05, 20240505
- Relative dates:
  • `NOW` or `0` - now
  • `-15D` - 15 days ago
  • `-2M` - 2 months ago
  • `-1Y` - 1 year ago
  • `-1Y-2M-15D` - 1 year, 2 months, and 7 days ago
  • `-1Y+2M+15D` - 9 months, and 15 days ago
    """
    bot.reply_to(message, welcome_text, parse_mode="Markdown")


@bot.message_handler(func=lambda message: True)
def handle_date_input(message):
    chat_id = message.chat.id
    try:
        result = parse_date_and_time(message.text)

        gregorian_day = str(result)[:10]
        jalali_day = convert_to_jalali(str(result))
        input_time = str(result)[11:16]

        if result > dt.now(tehran_tz):
            txt = "You selected a future date report. That date hasn’t arrived yet 🗿"
            bot.reply_to(message, txt)
            return
        else:
            txt = f"✅ Date and Time parsed successfully!\nGregorian: {gregorian_day}\nJalali: {jalali_day}\nTime: {input_time}\n🔍 Searching for the first message of this day..."
            bot.reply_to(message, txt)

        # Get the closest message for that datetime
        msg = get_nearest_data(result)

        if msg and "message_id" in msg:
            try:
                msg_id = int(msg["message_id"])
                bot.forward_message(chat_id, f"@{CHANNEL_USERNAME}", msg_id)
            except Exception as e:
                txt = get_text(msg)
                utc_dt = pytz.utc.localize(msg["timestamp"])
                tehran_dt = utc_dt.astimezone(tehran_tz)
                txt += f"\n\n{to_jalali(tehran_dt)}"
                bot.send_message(
                    chat_id,
                    txt,
                    parse_mode="Markdown",
                    disable_web_page_preview=True,
                )
        elif msg:
            txt = get_text(msg)
            utc_dt = pytz.utc.localize(msg["timestamp"])
            tehran_dt = utc_dt.astimezone(tehran_tz)
            txt += f"\n\n{to_jalali(tehran_dt)}"
            bot.send_message(
                chat_id,
                txt,
                parse_mode="Markdown",
                disable_web_page_preview=True,
            )
        else:
            txt = f"📭 No messages available on {gregorian_day} at {input_time}"
            bot.reply_to(message, txt)
    except ValueError as e:
        error = (
            f"{str(e)}\n\nPlease enter a valid date using one of the supported formats."
        )
        bot.reply_to(message, error)
        add_log(str(e))
    except Exception as e:
        error = f"❌ An error occurred:\n{str(e)}"
        bot.reply_to(message, error)
        add_log(error)


def convert_to_jalali(date_str):
    try:
        gregorian_dt = dt.strptime(date_str[:10], "%Y-%m-%d")
        jd = jdatetime.date.fromgregorian(date=gregorian_dt)
        return jd.strftime("%Y-%m-%d")
    except ValueError as e:
        error = f"Exception in convert_to_jalali:\n{e}"
        add_log(error)
        return None


if __name__ == "__main__":
    if PROXY_SERVER and PROXY_PORT:
        proxy_url = f"socks5h://{PROXY_SERVER}:{PROXY_PORT}"
        telebot.apihelper.proxy = {"http": proxy_url, "https": proxy_url}
    commands = [
        types.BotCommand(
            command="/start", description="Start interacting with the bot"
        ),
        types.BotCommand(command="/help", description="Help info"),
    ]
    bot.set_my_commands(commands)
    print("Bot is Polling ...")
    bot.polling()
    add_log(f"❌ Bot is down now ❌")
