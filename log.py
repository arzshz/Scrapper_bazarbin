import requests
import telebot

from secret import (
    PROXY_SERVER,
    PROXY_PORT,
    TELEGRAM_BOT_TOKEN,
    LOG_CHANNEL_ID,
    TOKEN_LOGGING,
)


def add_log(the_error):
    logging_bot = telebot.TeleBot(TOKEN_LOGGING)
    if PROXY_SERVER and PROXY_PORT:
        proxy_url = f"socks5h://{PROXY_SERVER}:{PROXY_PORT}"
        telebot.apihelper.proxy = {"http": proxy_url, "https": proxy_url}
    log_channel_id = LOG_CHANNEL_ID
    logging_bot.send_message(log_channel_id, f"{get_bot_username()} - {the_error}")


def get_bot_username(proxies=None):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe"
        if PROXY_SERVER and PROXY_PORT:
            proxies = {
                "http": f"socks5h://{PROXY_SERVER}:{PROXY_PORT}",
                "https": f"socks5h://{PROXY_SERVER}:{PROXY_PORT}",
            }
        response = requests.get(url, proxies=proxies)
        data = response.json()
        if data["ok"]:
            return data["result"]["username"]
        return None
    except Exception as e:
        print(f"Exception in get_bot_username: {e}")
        return None
