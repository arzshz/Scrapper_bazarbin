import asyncio
import datetime
import os
import threading
from datetime import datetime as dt

import jdatetime
import telebot
from dotenv import load_dotenv
from telethon import TelegramClient

from parsers import parse_date_and_time

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
telethon_loop = None  # Store the event loop used for Telethon


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
            start_of_day = datetime.datetime.combine(target_date, datetime.time.min).replace(
                tzinfo=datetime.timezone.utc
            )
            print("Calculate datetime boundaries for the target day - P2")
            end_of_day = datetime.datetime.combine(target_date, datetime.time.max).replace(
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

    # Use the same event loop as Telethon client
    if telethon_loop is None or not telethon_loop.is_running():
        print("Telethon event loop not available")
        return []

    try:
        future = asyncio.run_coroutine_threadsafe(async_get_first_message(), telethon_loop)
        result = future.result(timeout=30)  # 30 second timeout
        return result
    except Exception as e:
        print(f"Error in event loop: {e}")
        return []


async def async_get_closest_message(target_dt: datetime.datetime):
    global client

    if client is None:
        print("Telethon client not initialized")
        return []

    try:
        # Get the channel entity
        entity = await client.get_entity(CHANNEL_USERNAME)

        # Fetch a few messages around the target datetime
        # offset_date means "start fetching messages older than this date"
        messages = []
        async for msg in client.iter_messages(entity, offset_date=target_dt, limit=10):
            messages.append(msg)

        # Also fetch newer messages (reverse=True gives ascending order)
        async for msg in client.iter_messages(entity, offset_date=target_dt, reverse=True, limit=10):
            messages.append(msg)

        if not messages:
            print("No messages found near this datetime")
            return []

        # Find the closest message by absolute time difference
        closest = min(messages, key=lambda m: abs((m.date - target_dt).total_seconds()))

        # Format message content
        if closest.text:
            message_text = closest.text
        elif closest.media:
            message_text = f"[Media: {closest.media.__class__.__name__}]"
        else:
            message_text = "[Empty message]"

        return [
            {
                "id": closest.id,
                "date": closest.date,
                "text": message_text,
                "is_media": closest.media is not None,
                "message_obj": closest,
            }
        ]

    except Exception as e:
        print(f"Error retrieving messages: {e}")
        return []


def get_closest_message(target_dt: datetime.datetime):
    """
    Get the closest message to a specific datetime using Telethon.
    Returns the message nearest to the given datetime.
    """
    # Use the same event loop as Telethon client
    if telethon_loop is None or not telethon_loop.is_running():
        print("Telethon event loop not available")
        return []

    try:
        future = asyncio.run_coroutine_threadsafe(async_get_closest_message(target_dt), telethon_loop)
        result = future.result(timeout=30)  # 30 second timeout
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
        try:
            # Parse the date
            result = parse_date_and_time(message.text)

            gregorian_day = str(result)[:10]
            jalali_day = convert_to_jalali(str(result))
            input_time = str(result)[11:16]

            # Send confirmation
            bot.reply_to(
                message,
                f"✅ Date and Time parsed successfully!\n"
                f"Gregorian: {gregorian_day}\n"
                f"Jalali: {jalali_day}\n"
                f"Time: {input_time}\n"
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

            # Get the closest message for that datetime
            messages = get_closest_message(result)

            if messages:
                for msg in messages:
                    # Try to forward the original message if it's media
                    # if msg["is_media"]:
                    try:
                        # Forward the original media message
                        print("try forwarding")
                        print(msg['id'])
                        bot.forward_message(chat_id, f"@{CHANNEL_USERNAME}", int(msg["id"]))
                        # Also send the text description
                        # print("try sending")
                        # bot.send_message(chat_id, message_text, parse_mode="Markdown")
                    except Exception as e:
                        # If forwarding fails, just send the text
                        print(f"Exception:\n{e}")
                        bot.send_message(
                            chat_id,
                            "\n".join(msg['text'].split("\n")[:-1]),
                            parse_mode="Markdown",
                            disable_web_page_preview = True
                        )
                    # else:
                    # For text messages, just send the content
                    # print("else try sending")
                    # bot.send_message(chat_id, "\n".join(msg['text'].split("\n")[:-1]), parse_mode="Markdown", disable_web_page_preview=True)
            else:
                bot.reply_to(message, f"📭 No messages available on {gregorian_day} at {input_time}")

            # Reset user state
            user_states[chat_id] = {"waiting_for_date": False}

        except ValueError as e:
            bot.reply_to(
                message,
                f"❌ {str(e)}\n\nPlease send a valid date in one of the supported formats.",
            )
        except Exception as e:
            bot.reply_to(message, f"❌ An error occurred: {str(e)}")

    else:
        # User sent a message without using /getdate first
        try:
            target_date = parse_date_and_time(message.text)
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
        gregorian_dt = dt.strptime(date_str[:10], "%Y-%m-%d")
        # Convert to a Jalali ``jdatetime`` object
        jd = jdatetime.date.fromgregorian(date=gregorian_dt)

        return jd.strftime("%Y-%m-%d")
    except ValueError as e:
        return None


# ===== INITIALIZATION AND MAIN LOOP =====
def initialize_telethon_sync():
    """Initialize Telethon client in a separate thread with persistent event loop"""
    global telethon_loop

    def run_telethon_loop():
        global telethon_loop
        telethon_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(telethon_loop)

        try:
            # Initialize the client
            success = telethon_loop.run_until_complete(initialize_telethon())
            if success:
                print("✅ Telethon client initialized successfully")
            else:
                print("❌ Failed to initialize Telethon client")
                return

            # Keep the event loop running forever
            telethon_loop.run_forever()
        except Exception as e:
            print(f"❌ Error in Telethon event loop: {e}")
        finally:
            telethon_loop.close()

    telethon_thread = threading.Thread(target=run_telethon_loop, daemon=True)
    telethon_thread.start()

    # Wait a bit for initialization
    import time
    time.sleep(2)


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
            if telethon_loop and telethon_loop.is_running():
                asyncio.run_coroutine_threadsafe(client.disconnect(), telethon_loop)
            print("Telethon client disconnected")