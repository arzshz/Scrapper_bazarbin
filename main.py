import asyncio
import datetime
import threading
import time
from datetime import datetime as dt

import jdatetime
import telebot
from telebot import types
from telethon import TelegramClient

from log import add_log
from parsers import parse_date_and_time, tehran_tz
from secret import *

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
client = None
telethon_loop = None  # Store the event loop used for Telethon


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
        async for msg in client.iter_messages(
            entity, offset_date=target_dt, reverse=True, limit=10
        ):
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
        error = "Telethon event loop not available"
        print(error)
        add_log(error)
        return []

    try:
        future = asyncio.run_coroutine_threadsafe(
            async_get_closest_message(target_dt), telethon_loop
        )
        result = future.result(timeout=30)  # 30 second timeout
        return result
    except Exception as e:
        error = f"Error in event loop: {e}"
        print(error)
        add_log(error)
        return []


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

    # Check if user is in waiting for date state
    try:
        # Parse the date
        result = parse_date_and_time(message.text)

        gregorian_day = str(result)[:10]
        jalali_day = convert_to_jalali(str(result))
        input_time = str(result)[11:16]

        # Send confirmation
        if result > dt.now(tehran_tz):
            bot.reply_to(
                message,
                "You selected a future date report. That date hasn’t arrived yet 🗿",
            )
            return
        else:
            bot.reply_to(
                message,
                f"✅ Date and Time parsed successfully!\n"
                f"Gregorian: {gregorian_day}\n"
                f"Jalali: {jalali_day}\n"
                f"Time: {input_time}\n"
                f"🔍 Searching for the first message of this day...",
            )
            jalali_days = [
                jalali_day.replace("-", "/"),
                "/".join([str(int(num)) for num in jalali_day.split("-")]),
            ]

        # Check if Telethon client is ready
        if client is None or not client.is_connected():
            bot.reply_to(
                message,
                "❌ Telethon client is not ready. Please try again in a moment.",
            )
            return

        # Get the closest message for that datetime
        messages = get_closest_message(result)

        if (
            messages
            and messages[0]["text"]
            and (
                jalali_days[0] in messages[0]["text"]
                or jalali_days[1] in messages[0]["text"]
            )
        ):
            for msg in messages:
                # Try to forward the original message if it's media
                try:
                    # Forward the original media message
                    bot.forward_message(chat_id, f"@{CHANNEL_USERNAME}", int(msg["id"]))
                except Exception as e:
                    # If forwarding fails, just send the text
                    error = f"Exception in forwarding:\n{e}"
                    print(error)
                    add_log(error)
                    bot.send_message(
                        chat_id,
                        "\n".join(msg["text"].split("\n")[:-1]),
                        parse_mode="Markdown",
                        disable_web_page_preview=True,
                    )
        else:
            bot.reply_to(
                message, f"📭 No messages available on {gregorian_day} at {input_time}"
            )

    except ValueError as e:
        bot.reply_to(
            message,
            f"{str(e)}\n\nPlease enter a valid date using one of the supported formats.",
        )
    except Exception as e:
        error = f"❌ An error occurred:\n{str(e)}"
        bot.reply_to(message, error)
        add_log(error)


def convert_to_jalali(date_str):
    try:
        # Parse the Gregorian string to a ``datetime`` object
        gregorian_dt = dt.strptime(date_str[:10], "%Y-%m-%d")
        # Convert to a Jalali ``jdatetime`` object
        jd = jdatetime.date.fromgregorian(date=gregorian_dt)

        return jd.strftime("%Y-%m-%d")
    except ValueError as e:
        error = f"Exception in convert_to_jalali:\n{e}"
        add_log(error)
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
            error = f"❌ Error in Telethon event loop: {e}"
            print(error)
            add_log(error)
        finally:
            telethon_loop.close()

    telethon_thread = threading.Thread(target=run_telethon_loop, daemon=True)
    telethon_thread.start()

    time.sleep(2)


# ===== TELETHON CLIENT FUNCTIONS =====
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


if __name__ == "__main__":
    # Initialize Telethon client
    print("🔧 Initializing Telethon client...")
    initialize_telethon_sync()

    try:
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
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as err:
        print(f"❌ Bot error:\n{err}")
        add_log(f"❌ Bot error:\n{err}")
    finally:
        # Close Telethon client when bot stops
        if client and client.is_connected():
            if telethon_loop and telethon_loop.is_running():
                asyncio.run_coroutine_threadsafe(client.disconnect(), telethon_loop)
            print("Telethon client disconnected")
            add_log("Telethon client disconnected")
