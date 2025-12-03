from datetime import datetime as dt

import jdatetime
import pytz
import telebot
from telebot import types

from get_text_from_db import get_text
from log import add_log
from parsers import parse_date_and_time, tehran_tz, english_to_persian
from secret import *

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

from datetime import timedelta, timezone
from pymongo import ASCENDING, MongoClient

mongo_client = MongoClient("mongodb://localhost:27017/")
db = mongo_client["bazarbin_data"]
collection = db["prices"]


# ===== TELEGRAM BOT HANDLERS =====
@bot.message_handler(commands=["start"])
def send_welcome(message):
    welcome_text = """
..:: بات بازاربین ::..

با ارسال یک تاریخ یا ساعت، اطلاعات بازار در آن زمان را دریافت کنید.


راهنمای وارد کردن تاریخ و ساعت (فرمت های قابل قبول):
/input_help
    """
    bot.reply_to(message, welcome_text)


@bot.message_handler(commands=["input_help"])
def input_help_handler(message):
    help_message = """..::  راهنمای وارد کردن تاریخ و ساعت  ::..

- تاریخ شمسی و میلادی در فرمت های مختلف قابل قبول است.

- بین اجزای تاریخ امکان قرارگیری - یا / یا فاصله (space) وجود دارد. امکان اینکه چیزی قرار نگیرد هم وجود دارد.

- تاریخ بدون وارد کردن صفر ها هم ممکن است قابل قبول باشد.
   • مثلا ۱۴۰۴۱۱ قابل قبول است.
   • اما ۱۴۰۴۱۱۱ قابل قبول نیست چون امکان تشخیص اینکه ۱۱ فروردین است یا ۱ بهمن وجود ندارد.

- تاریخ را می توان به شکل وابسته به زمان حال وارد کرد.
   • بعنوان مثال برای یک سال و دو روز پیش بنویسید:
<blockquote>-1y-2d</blockquote>
   • بعنوان مثال برای ۱۱ ماه پیش بنویسید:
<blockquote>-1y+1m</blockquote>
   یا
<blockquote>-11m</blockquote>

- ساعت بر اساس منطقه زمانی ایران هست.

- بین اجزا ساعت امکان قرارگیری : یا فاصله (space) وجود دارد. امکان اینکه چیزی قرار نگیرد هم وجود دارد.

- ساعت را می توان به شکل وابسته به زمان حال وارد کرد.
   • بعنوان مثال برای دو ساعت قبل بنویسید:
<blockquote>-2h</blockquote>

- ۰ یا now به معنی «همین الان» است.

- فقط اطلاعات بعد از ۱۴۰۲/۰۱/۱۸ یا ۲۰۲۳/۰۴/۰۷ در دسترس هستند.
"""
    bot.send_message(message.chat.id, help_message, parse_mode="HTML")


@bot.message_handler(func=lambda message: True)
def handle_date_input(message):
    chat_id = message.chat.id
    try:
        result = parse_date_and_time(message.text)

        gregorian_day = str(result)[:10]
        jalali_day = convert_to_jalali(str(result))
        input_time = str(result)[11:16]

        if result > dt.now(tehran_tz):
            txt = "پیشبینی اطلاعات بازار در آینده از عهده ما خارج است 🗿"
            bot.reply_to(message, txt)
            return
        else:
            greg = english_to_persian(gregorian_day).replace("-", "/")
            shamsi = english_to_persian(jalali_day).replace("-", "/")
            txt = f"✅ ساعت و تاریخ دریافت شدند.\nمیلادی: {greg}\nشمسی: {shamsi}\nساعت: {english_to_persian(input_time)}\n🔍 در تلاش برای یافتن اطلاعات بازار در تاریخ و ساعت مورد نظر هستیم ..."
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
            txt = "📭 پیامی یافت نشد."
            bot.reply_to(message, txt)
    except ValueError as e:
        err = f"{str(e)}\nراهنمای وارد کردن تاریخ و ساعت (فرمت های قابل قبول):\n/input_help"
        bot.reply_to(message, err)
        add_log(
            f"ValueError in parse_date_and_time:\nMessage Text: {message.text}\n{str(e)}"
        )
    except Exception as e:
        error = f"❌ مشکلی پیش آمده:\n{str(e)}"
        bot.reply_to(message, error)
        add_log(error)


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
        types.BotCommand(command="/start", description="شروع"),
        types.BotCommand(
            command="/input_help", description="راهنمای وارد کردن تاریخ و ساعت"
        ),
    ]
    bot.set_my_commands(commands)
    print("Bot is Polling ...")
    add_log(f"Bot Started at {dt.now(tehran_tz).strftime('%Y-%m-%d %H:%M:%S')}")
    bot.polling()
    add_log(f"Bot Stopped at {dt.now(tehran_tz).strftime('%Y-%m-%d %H:%M:%S')}")
