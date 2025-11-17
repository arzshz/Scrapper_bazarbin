import re
from typing import Literal

lines = None


def get_data(text):
    data_dict = get_data_dict()
    s_usd, e_usd, s_usdt, e_usdt, s_gold, e_gold, s_gas, e_gas, s_crypto, e_crypto = [None for i in range(10)]
    global lines
    lines = text.split("\n")
    for idx, line in enumerate(lines):
        if "دلار (USD)" in line:
            s_usd = idx + 1
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
            "usd": {
                "fardayie": {
                    "sabze": {"buy": "", "sell": ""},
                    "tehran": {"buy": "", "sell": ""},
                },
                "naghdi": {
                    "sabze": {"buy": "", "sell": ""},
                    "tehran": {"buy": "", "sell": ""},
                },
                "bonbast": {"buy": "", "sell": ""},
                "tgju": {"price": ""},
            },
            "usdt": {
                "nobitex_150": {"ask": "", "bid": ""},
                "nobitex_5000": {"ask": "", "bid": ""},
                "wallex": {"ask": "", "bid": ""},
                "bitpin": {"ask": "", "bid": ""},
                "ramzinex": {"ask": "", "bid": ""},
            },
        },
        "gold_prices": {
            "tala.ir": {
                "ounce": {"price": ""},
                "tehran_market_price": {"price": ""},
                "18_karat_gold": {"price": ""},
                "old_coin": {"price": ""},
                "new_coin": {"price": ""},
                "quarter_coin": {"price": ""},
            }
        },
        "crypto": {
            "eth_gas": [],
            "btc": {"price": ""},
            "eth": {"price": ""},
            "bnb": {"price": ""},
        },
        "timestamp": None,
    }


def fill_usd(final_dict, start, end):
    for i in range(start, end + 1):
        if '|' in lines[i]:
            parts = lines[i].split('|')
            buy = to_int(parts[0].split(':')[-1].strip())
            sell = to_int(parts[1].strip())
            f_sabze = final_dict['currency_rates']['usd']['fardayie']['sabze']
            f_tehran = final_dict['currency_rates']['usd']['fardayie']['tehran']
            n_sabze = final_dict['currency_rates']['usd']['naghdi']['sabze']
            n_tehran = final_dict['currency_rates']['usd']['naghdi']['tehran']
            if 'فردایی' in lines[i]:
                f_sabze['buy'], f_tehran['buy'] = buy, buy
                f_sabze['sell'], f_tehran['sell'] = sell, sell
            elif 'نقدی' in lines[i]:
                n_sabze['buy'], n_tehran['buy'] = buy, buy
                n_sabze['sell'], n_tehran['sell'] = sell, sell
            elif 'سبزه' in lines[i]:
                n_sabze['buy'], n_sabze['sell'] = buy, sell
            elif 'تهران' in lines[i]:
                n_tehran['buy'], n_tehran['sell'] = buy, sell
            elif 'بن‌بست' in lines[i]:
                final_dict['currency_rates']['usd']['bonbast']['buy'] = buy
                final_dict['currency_rates']['usd']['bonbast']['sell'] = sell
        elif lines[i] and 'tgju' in lines[i]:
            price = to_int(lines[i].split(':')[-1].strip())
            final_dict['currency_rates']['usd']['tgju']['price'] = price
    return final_dict


def fill_usdt(final_dict, start, end):
    for i in range(start, end + 1):
        if lines[i]:
            name = re.search(r'\[(.* ?)\]', lines[i]).group(1).lower()
            parts = lines[i].split('|')
            bid = to_int(parts[0].split(':')[-1].replace('✴️', '').replace('❇️', '').strip())
            ask = to_int(parts[1].replace('✴️', '').replace('❇️', '').strip())
            final_dict['currency_rates']['usdt'][name]['bid'] = bid
            final_dict['currency_rates']['usdt'][name]['ask'] = ask
    return final_dict


def fill_gold(final_dict, start, end):
    gold_dict = {'اونس طلا': 'ounce', 'مظنه بازار تهران': 'tehran_market_price', 'طلای 18 عیار': '18_karat_gold',
                 'سکه قدیم': 'old_coin', 'سکه جدید': 'new_coin', 'ربع سکه': 'quarter_coin'}
    for i in range(start, end + 1):
        for key, value in gold_dict.items():
            if key in lines[i]:
                price = to_int(lines[i].split(':')[-1].replace('$', '').strip())
                final_dict['gold_prices']['tala.ir'][value]['price'] = price
    return final_dict


def fill_gas(final_dict, start, end):
    for i in range(start, end + 1):
        if lines[i]:
            parts = [p.strip() for p in lines[i].split('|')]
            prices = [parts[-3].split(':')[-1].strip(), parts[-2], parts[-1]]
            new_prices = []
            for price in prices:
                if price != "خطا":
                    new_prices.append(float(price))
            final_dict['crypto']['eth_gas'].extend(new_prices)
    return final_dict


def fill_crypto(final_dict, start, end):
    coin_dict = {'بیت‌کوین': 'btc', 'اتر': 'eth', 'بی‌ان‌بی': 'bnb'}
    for i in range(start, end + 1):
        for key, value in coin_dict.items():
            if key in lines[i]:
                price = to_int(lines[i].split(':')[-1].replace('$', '').strip())
                final_dict['crypto'][value]['price'] = price
    return final_dict


def to_int(price: str) -> Literal["خطا"] | float | int:
    if price == "خطا":
        return price
    elif "." in price:
        return float(price)
    else:
        return int(price.replace(",", ""))

# inp = """دلار (USD)
# فردایی [سبزه](https://t.me/tahran_sabza/681057) و [تهران](https://t.me/dollar_tehran3bze/696182): 112,000 | 111,950
# نقدی [سبزه](https://t.me/tahran_sabza/681014) و [تهران](https://t.me/dollar_tehran3bze/696139): 111,900 | 111,850
# [بن‌بست](https://www.bonbast.com/): 111,550 | 111,450
# [سایت tgju (آزاد)](https://www.tgju.org/قیمت-دلار): 111,980
#
#
# USDT (تتر)
# [Nobitex_150](https://nobitex.ir/panel/exchange/usdt-irt/): 112,905 | 112,895 ❇️
# [Nobitex_5000](https://nobitex.ir/panel/exchange/usdt-irt/): 112,905 | 112,836
# [Wallex](https://wallex.ir/): 112,740 | 112,739
# [Bitpin](https://bitpin.ir/): ✴️ 112,685 | 112,685
# [Ramzinex](https://ramzinex.com/): 112,850 | 112,770
#
#
# طلا (GOLD) (بر اساس tala.ir)
# [اونس طلا](https://www.tala.ir/gold-price): 4,082$
# [مظنه بازار تهران](https://www.tala.ir/gold-price): 47,887,000
# [طلای 18 عیار](https://www.tala.ir/gold-price): 11,054,700
# [سکه قدیم](https://www.tala.ir/gold-price): 109,500,000
# [سکه جدید](https://www.tala.ir/gold-price): 115,200,000
# [ربع سکه](https://www.tala.ir/gold-price): 33,800,000
#
#
# Ethereum Gas
# [Etherscan](https://etherscan.io/gastracker): 0.125 | 0.105 | 0.115
#
#
# رمز ارز (Cryptocurrency)
# [بیت‌کوین](https://www.binance.com/en/trade/BTCUSDT): 95,620$
# [اتر](https://www.binance.com/en/trade/ETHUSDT): 3,173$
# [بی‌ان‌بی (BNB)](https://www.binance.com/en/trade/BNBUSDT): 938$
#
# 1404/08/25   18:15
#
#
# 🆔 @bazar_bin"""
