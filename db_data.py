import re
from typing import Literal

lines = None


def get_data(text):
    data_dict = get_data_dict()
    s_usd, e_usd, s_usdt, e_usdt, s_gold, e_gold, s_gas, e_gas, s_crypto, e_crypto = [
        None for i in range(10)
    ]
    global lines
    lines = text.split("\n")
    for idx, line in enumerate(lines):
        if "دلار (USD)" in line:
            s_usd = idx + 1
            data_dict["currency_rates"]["usd"] = {}
        elif "USDT (تتر)" in line:
            if s_usd:
                e_usd = idx - 1
            s_usdt = idx + 1
        elif "طلا (GOLD)" in line:
            if s_usdt:
                e_usdt = idx - 1
            s_gold = idx + 1
        elif "Ethereum Gas" in line:
            if s_gold:
                e_gold = idx - 1
            s_gas = idx + 1
        elif "رمز ارز (Cryptocurrency)" in line:
            if s_gas:
                e_gas = idx - 1
            s_crypto = idx + 1
        elif line.startswith("1404"):
            if s_crypto:
                e_crypto = idx - 1

    if s_usd and e_usd:
        data_dict = fill_usd(data_dict, s_usd, e_usd)

    if s_usdt and e_usdt:
        data_dict = fill_usdt(data_dict, s_usdt, e_usdt)

    if s_gold and e_gold:
        data_dict = fill_gold(data_dict, s_gold, e_gold)

    if s_gas and e_gas:
        data_dict = fill_gas(data_dict, s_gas, e_gas)

    if s_crypto and e_crypto:
        data_dict = fill_crypto(data_dict, s_crypto, e_crypto)
    return data_dict


def get_data_dict():
    return {
        "currency_rates": {
            "usdt": {
                "nobitex_150": {"ask": "", "bid": ""},
                "nobitex_5000": {"ask": "", "bid": ""},
                "wallex": {"ask": "", "bid": ""},
                "bitpin": {"ask": "", "bid": ""},
                "ramzinex": {"ask": "", "bid": ""},
            },
        },
        "gold_prices": {"tala.ir": {}},
        "crypto": {
            "eth_gas": [],
        },
        "timestamp": None,
    }


def fill_usd(final_dict, start, end):
    for i in range(start, end + 1):
        if "|" in lines[i]:
            parts = lines[i].split("|")
            buy = to_int(parts[0].split(":")[-1].strip())
            sell = to_int(parts[1].strip())
            if "فردایی" in lines[i]:
                for ch in ("sabze", "tehran"):
                    if "fardayie" not in final_dict["currency_rates"]["usd"]:
                        final_dict["currency_rates"]["usd"].update(
                            {"fardayie": {ch: {"buy": buy, "sell": sell}}}
                        )
                    else:
                        final_dict["currency_rates"]["usd"]["fardayie"][ch] = {
                            "buy": buy,
                            "sell": sell,
                        }
            elif "نقدی" in lines[i]:
                for ch in ("sabze", "tehran"):
                    if "naghdi" not in final_dict["currency_rates"]["usd"]:
                        final_dict["currency_rates"]["usd"].update(
                            {"naghdi": {ch: {"buy": buy, "sell": sell}}}
                        )
                    else:
                        final_dict["currency_rates"]["usd"]["naghdi"][ch] = {
                            "buy": buy,
                            "sell": sell,
                        }
            elif "سبزه" in lines[i] or "تهران" in lines[i]:
                if "combination" not in final_dict["currency_rates"]["usd"]:
                    final_dict["currency_rates"]["usd"].update(
                        {"combination": {"buy": buy, "sell": sell}}
                    )
            elif "بن‌بست" in lines[i]:
                if "bonbast" not in final_dict["currency_rates"]["usd"]:
                    final_dict["currency_rates"]["usd"].update(
                        {"bonbast": {"buy": buy, "sell": sell}}
                    )
        elif lines[i] and "tgju" in lines[i]:
            price = to_int(lines[i].split(":")[-1].strip())
            if "tgju" not in final_dict["currency_rates"]["usd"]:
                final_dict["currency_rates"]["usd"].update({"tgju": {"price": price}})
    return final_dict


def fill_usdt(final_dict, start, end):
    for i in range(start, end + 1):
        if lines[i]:
            name = re.search(r"\[(.* ?)\]", lines[i]).group(1).lower()
            parts = lines[i].split("|")
            bid = to_int(
                parts[0].split(":")[-1].replace("✴️", "").replace("❇️", "").strip()
            )
            ask = to_int(parts[1].replace("✴️", "").replace("❇️", "").strip())
            final_dict["currency_rates"]["usdt"][name]["bid"] = bid
            final_dict["currency_rates"]["usdt"][name]["ask"] = ask
    return final_dict


def fill_gold(final_dict, start, end):
    gold_dict = {
        "اونس طلا": "ounce",
        "مظنه بازار تهران": "tehran_market_price",
        "طلای 18 عیار": "18_karat_gold",
        "سکه قدیم": "old_coin",
        "سکه جدید": "new_coin",
        "ربع سکه": "quarter_coin",
    }
    for i in range(start, end + 1):
        for key, value in gold_dict.items():
            if key in lines[i] and not final_dict["gold_prices"]["tala.ir"]:
                price = to_int(lines[i].split(":")[-1].replace("$", "").strip())
                final_dict["gold_prices"]["tala.ir"] = {value: {"price": price}}
            elif key in lines[i]:
                price = to_int(lines[i].split(":")[-1].strip())
                final_dict["gold_prices"]["tala.ir"][value] = {"price": price}
    return final_dict


def fill_gas(final_dict, start, end):
    for i in range(start, end + 1):
        if lines[i]:
            parts = [p.strip() for p in lines[i].split("|")]
            prices = [parts[-3].split(":")[-1].strip(), parts[-2], parts[-1]]
            new_prices = []
            for price in prices:
                if price != "خطا":
                    new_prices.append(float(price))
                else:
                    new_prices.append(price)
            final_dict["crypto"]["eth_gas"].extend(new_prices)
    return final_dict


def fill_crypto(final_dict, start, end):
    coin_dict = {"بیت‌کوین": "btc", "اتر": "eth", "بی‌ان‌بی": "bnb"}
    for i in range(start, end + 1):
        for key, value in coin_dict.items():
            if key in lines[i]:
                price = to_int(lines[i].split(":")[-1].replace("$", "").strip())
                final_dict["crypto"][value] = {"price": price}
    return final_dict


def to_int(price: str | None) -> Literal["خطا"] | float | int:
    if price == "خطا" or price is None:
        return "خطا"
    elif "." in str(price):
        return float(price)
    else:
        return int(str(price).replace(",", ""))
