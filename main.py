import asyncio
import datetime
import os
import threading
from datetime import datetime as dt

import jdatetime
import pytz
import telebot
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv
from telethon import TelegramClient

load_dotenv()

# ===== CONFIGURATION =====
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")  # Channel username (without @)
PROXY_SERVER = os.getenv("PROXY_SERVER")
PROXY_PORT = os.getenv("PROXY_PORT")

# ===== INITIALIZE BOT =====
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# ===== GLOBAL VARIABLES =====
client = None
user_states = {}


# ===== DATE PARSING FUNCTIONS =====
def persian_to_english(text):
    """Convert Persian/Farsi numbers to English"""
    persian_numbers = "۰۱۲۳۴۵۶۷۸۹"
    english_numbers = "0123456789"
    translation_table = str.maketrans(persian_numbers, english_numbers)
    return text.translate(translation_table)


def parse_month_day(month_day: str):
    """
    Parse a month+day string into integers.
    Supported formats:
      - MMDD (4 chars)
      - MDD or MMD (3 chars, but ambiguous → error if both valid)
      - MD (2 chars)
    """
    if len(month_day) == 4:  # MMDD
        month = int(month_day[:2])
        day = int(month_day[2:])
    elif len(month_day) == 3:
        # Could be MDD or MMD → ambiguous if both interpretations are valid
        m1, d1 = int(month_day[0]), int(month_day[1:])  # MDD
        m2, d2 = int(month_day[:2]), int(month_day[2:])  # MMD

        valid_m1 = 1 <= m1 <= 12
        valid_m2 = 1 <= m2 <= 12

        if valid_m1 and not valid_m2:
            month, day = m1, d1
        elif valid_m2 and not valid_m1:
            month, day = m2, d2
        else:
            raise ValueError(
                f"❌ Ambiguous date. Use separators like YYYY-MM-DD or YYYY/MM/DD."
            )
    elif len(month_day) == 2:  # MD
        month = int(month_day[0])
        day = int(month_day[1])
    else:
        raise ValueError(f"❌ Invalid date format.")

    return month, day


def parse_relative_date(s: str):
    """
    Parse a string like '15D2Y34M' or '39M-4Y2M' into (year, month, day) in Tehran timezone.
    Special cases:
      - '0' or 'NOW' => today's date
    Units:
      Y = years, M = months, D = days
    """
    tehran = pytz.timezone("Asia/Tehran")
    now = dt.now(tehran)
    if s == "0" or s == "NOW":
        return now.year, now.month, now.day
    direction = -1 if "-" in s else 1
    clean = s.replace("-", "").replace("+", "")
    years = months = days = 0
    num = ""
    for ch in clean:
        if ch.isdigit():
            num += ch
        else:
            if not num:
                continue
            value = int(num)
            if ch == "Y":
                years += value
            elif ch == "M":
                months += value
            elif ch == "D":
                days += value
            num = ""  # reset

    # Apply offset
    years, months, days = direction * years, direction * months, direction * days
    if years != 0 or months != 0 or days != 0:
        delta = relativedelta(years=years, months=months, days=days)
        target = now + delta
        return target.year, target.month, target.day
    else:
        raise ValueError("❌ Invalid date format.")


def parse_date(date_str: str) -> datetime.date:
    date_str = persian_to_english(date_str.strip())
    date_str = date_str.replace(" ", "")
    year, month, day = None, None, None
    relative_date = ["Y", "M", "D", "NOW"]
    for d in relative_date:
        if d in date_str.upper() or date_str == "0":
            year, month, day = parse_relative_date(date_str.upper())
            break
    if not (year or month or day):
        sep = ["/", "-"]
        for s in sep:
            if s in date_str:
                year, month, day = map(int, date_str.split(s))
                is_digit = "N"
                break
        else:
            is_digit = "T" if date_str.isdigit() else "F"

        if is_digit == "F" or (is_digit == "T" and len(date_str) < 6):
            raise ValueError("❌ Invalid date format.")
        elif is_digit == "T":
            year = int(date_str[:4])
            month, day = parse_month_day(date_str[4:])

    if 1394 < year < 1425 and 0 < month < 13 and 0 < day < 32:
        jdate = str(jdatetime.date(year, month, day).togregorian()).replace("-", "/")
        return jdate
    elif 2014 < year < 2045 and 0 < month < 13 and 0 < day < 32:
        date_obj = dt(year, month, day).date().replace("-", "/")
        return date_obj
    else:
        raise ValueError("❌ Invalid date format.")


# ===== TELETHON CLIENT FUNCTIONS =====
async def create_telethon_client():
    """Create and start Telethon client"""
    global client
    if PROXY_SERVER and PROXY_PORT:
        client = TelegramClient(
            "scraper", API_ID, API_HASH, proxy=("socks5", PROXY_SERVER, int(PROXY_PORT))
        )
    else:
        client = TelegramClient("scraper", API_ID, API_HASH)
    await client.start()
    print("Telethon client started successfully")
    return client


async def initialize_telethon():
    """Initialize Telethon client"""
    global client
    try:
        client = await create_telethon_client()
        print("Telethon client initialized successfully")
        return True
    except Exception as e:
        print(f"Failed to initialize Telethon client: {e}")
        return False


def get_first_message_of_day(target_date: datetime.date):
    """
    Get the first message from channel for a specific date using Telethon.
    Returns the first message sent on that day.
    """

    async def async_get_first_message():
        global client

        if client is None:
            print("Telethon client not initialized")
            return []

        try:
            # Get the channel entity
            print("Get the channel entity")
            entity = await client.get_entity(CHANNEL_USERNAME)
            print("Get the channel entity")

            # Calculate datetime boundaries for the target day
            print("Calculate datetime boundaries for the target day - P1")
            start_of_day = datetime.combine(target_date, datetime.time.min).replace(
                tzinfo=datetime.timezone.utc
            )
            print("Calculate datetime boundaries for the target day - P2")
            end_of_day = datetime.combine(target_date, datetime.time.max).replace(
                tzinfo=datetime.timezone.utc
            )

            print(f"Searching for first message on {target_date}")
            print(f"Time range: {start_of_day} to {end_of_day}")

            # First, check if there are any messages on this day
            message_count = 0
            async for message in client.iter_messages(
                entity, offset_date=end_of_day, limit=5
            ):
                if start_of_day <= message.date <= end_of_day:
                    message_count += 1

            if message_count == 0:
                print("No messages found for this date")
                return []

            # Now find the first message of the day
            first_message = None
            async for message in client.iter_messages(
                entity,
                offset_date=start_of_day,
                reverse=True,  # Start from the beginning of the day
                limit=20,
            ):
                if message.date >= start_of_day:
                    first_message = message
                else:
                    break

            if first_message and start_of_day <= first_message.date <= end_of_day:
                # Format message content
                message_text = ""
                if first_message.text:
                    message_text = first_message.text
                elif first_message.media:
                    message_text = f"[Media: {first_message.media.__class__.__name__}]"
                else:
                    message_text = "[Empty message]"

                return [
                    {
                        "id": first_message.id,
                        "date": first_message.date,
                        "text": message_text,
                        "is_media": first_message.media is not None,
                        "message_obj": first_message,
                    }
                ]
            else:
                return []

        except Exception as e:
            print(f"Error retrieving messages: {e}")
            return []

    # Run the async function
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(async_get_first_message())
        loop.close()
        return result
    except Exception as e:
        print(f"Error in event loop: {e}")
        return []


# ===== TELEGRAM BOT HANDLERS =====
@bot.message_handler(commands=["start"])
def send_welcome(message):
    user_states[message.chat.id] = {"waiting_for_date": False}

    welcome_text = """
🤖 **Date Message Forwarder Bot**

Send me a date and I'll find the first message from the channel for that date!

**Supported date formats:**
- **Jalali/Persian**: 1403/02/15, 14030215
- **Gregorian**: 2024/05/05, 20240505
- **Relative dates**:
  - `NOW` or `0` - Today
  - `15D` - 15 days from now
  - `2M` - 2 months from now
  - `1Y` - 1 year from now
  - `-7D` - 7 days ago

**Examples:**
- `1403/02/15`
- `2024-05-05`
- `15D` (15 days from now)
- `-7D` (7 days ago)
- `NOW` (today)

Use /getdate to search for messages! 📅
    """
    bot.reply_to(message, welcome_text, parse_mode="Markdown")


@bot.message_handler(commands=["getdate"])
def ask_for_date(message):
    user_states[message.chat.id] = {"waiting_for_date": True}
    bot.reply_to(
        message, "📅 Please send me the date you want to get the first message for:"
    )


@bot.message_handler(commands=["status"])
def check_status(message):
    """Check if Telethon client is connected"""
    status = (
        "✅ Telethon client is connected"
        if client and client.is_connected()
        else "❌ Telethon client is not connected"
    )
    bot.reply_to(message, f"Bot Status:\n{status}")


@bot.message_handler(func=lambda message: True)
def handle_date_input(message):
    chat_id = message.chat.id

    # Check if user is in waiting for date state
    if chat_id in user_states and user_states[chat_id].get("waiting_for_date", False):
        # try:
        # Parse the date
        result = parse_date(message.text)

        if check_calendar_type(result) == "Jalali":
            gregorian_day = convert_to_gregorian(result)
            jalali_day = result
        else:
            gregorian_day = result
            jalali_day = convert_to_jalali(result)

        # Send confirmation
        bot.reply_to(
            message,
            f"✅ Date parsed successfully!\n"
            f"Gregorian: {gregorian_day}\n"
            f"Jalali: {jalali_day}\n\n"
            f"🔍 Searching for the first message of this day...",
        )

        # Check if Telethon client is ready
        if client is None or not client.is_connected():
            bot.reply_to(
                message,
                "❌ Telethon client is not ready. Please try again in a moment.",
            )
            user_states[chat_id] = {"waiting_for_date": False}
            return

        # Get the first message for that date
        messages = get_first_message_of_day(gregorian_day)

        if messages:
            for msg in messages:
                # Format the message info
                message_text = f"📅 **First Message of {result}**\n"
                message_text += (
                    f"🕒 **Time**: {msg['date'].strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
                )
                message_text += f"📝 **Content**:\n{msg['text']}"

                # Try to forward the original message if it's media
                if msg["is_media"]:
                    try:
                        # Forward the original media message
                        bot.forward_message(chat_id, CHANNEL_USERNAME, msg["id"])
                        # Also send the text description
                        bot.send_message(chat_id, message_text, parse_mode="Markdown")
                    except Exception as e:
                        # If forwarding fails, just send the text
                        bot.send_message(
                            chat_id,
                            f"{message_text}\n\n⚠️ *Could not forward media message*",
                            parse_mode="Markdown",
                        )
                else:
                    # For text messages, just send the content
                    bot.send_message(chat_id, message_text, parse_mode="Markdown")
        else:
            bot.reply_to(message, f"📭 No messages found for {result}")

        # Reset user state
        user_states[chat_id] = {"waiting_for_date": False}

    # except ValueError as e:
    #     bot.reply_to(
    #         message,
    #         f"❌ {str(e)}\n\nPlease send a valid date in one of the supported formats.",
    #     )
    # except Exception as e:
    #     bot.reply_to(message, f"❌ An error occurred: {str(e)}")

    else:
        # User sent a message without using /getdate first
        try:
            target_date = parse_date(message.text)
            jdate = jdatetime.date.fromgregorian(date=target_date)

            bot.reply_to(
                message,
                f"✅ Date parsed successfully!\n"
                f"Gregorian: {target_date}\n"
                f"Jalali: {jdate}\n\n"
                f"Use /getdate command to search for the first message from this date.",
            )

        except ValueError as e:
            bot.reply_to(
                message, f"❌ {str(e)}\n\nUse /start to see supported date formats."
            )
        except Exception as e:
            bot.reply_to(message, f"❌ An error occurred: {str(e)}")


# Error handler for media messages
@bot.message_handler(
    func=lambda message: True,
    content_types=["audio", "video", "document", "photo", "sticker"],
)
def handle_media(message):
    bot.reply_to(
        message,
        "📅 Please send a date in text format. Use /start to see supported formats.",
    )


def check_calendar_type(input_day):
    year = int(input_day[:4])

    if 1300 <= year <= 1500:
        return "Jalali"
    else:
        return "Gregorian"


def convert_to_gregorian(date_str):
    try:
        jalali_date = jdatetime.datetime.strptime(date_str, "%Y/%m/%d").date()
        gregorian_date = jalali_date.togregorian()
        return gregorian_date.strftime("%Y/%m/%d")
    except ValueError as e:
        return None


def convert_to_jalali(date_str):
    try:
        # Parse the Gregorian string to a ``datetime`` object
        gregorian_dt = dt.strptime(date_str, "%Y/%m/%d")
        # Convert to a Jalali ``jdatetime`` object
        jd = jdatetime.date.fromgregorian(date=gregorian_dt)

        return jd.strftime("%Y/%m/%d")
    except ValueError as e:
        return None


# ===== INITIALIZATION AND MAIN LOOP =====
def initialize_telethon_sync():
    """Initialize Telethon client in a separate thread"""

    def init():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            success = loop.run_until_complete(initialize_telethon())
            if success:
                print("✅ Telethon client initialized successfully")
            else:
                print("❌ Failed to initialize Telethon client")
        except Exception as e:
            print(f"❌ Error initializing Telethon client: {e}")
        finally:
            loop.close()

    telethon_thread = threading.Thread(target=init)
    telethon_thread.daemon = True
    telethon_thread.start()


if __name__ == "__main__":
    print("🚀 Starting Date Message Forwarder Bot...")

    # Initialize Telethon client
    print("🔧 Initializing Telethon client...")
    initialize_telethon_sync()

    # Start the bot
    print("🤖 Bot is running...")
    print("Commands available:")
    print("- /start - Show welcome message")
    print("- /getdate - Search for first message of a date")
    print("- /status - Check connection status")

    try:
        if PROXY_SERVER and PROXY_PORT:
            proxy_url = f"socks5h://{PROXY_SERVER}:{PROXY_PORT}"
            telebot.apihelper.proxy = {"http": proxy_url, "https": proxy_url}
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        print(f"❌ Bot error: {e}")
    finally:
        # Close Telethon client when bot stops
        if client and client.is_connected():
            client.disconnect()
            print("Telethon client disconnected")
