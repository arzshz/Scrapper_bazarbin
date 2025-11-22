gold_dict = {
    "ounce": "اونس طلا",
    "tehran_market_price": "مظنه بازار تهران",
    "18_karat_gold": "طلای 18 عیار",
    "old_coin": "سکه قدیم",
    "new_coin": "سکه جدید",
    "quarter_coin": "ربع سکه",
}
coin_dict = {
    "btc": "بیت‌کوین",
    "eth": "اتر",
    "bnb": "بی‌ان‌بی (BNB)",
    "pol": "ماتیک",
    "ftm": "فانتوم",
    "xmr": "مونرو",
}
coin_link = {
    "btc": "https://www.binance.com/en/trade/BTCUSDT",
    "eth": "https://www.binance.com/en/trade/ETHUSDT",
    "bnb": "https://www.binance.com/en/trade/BNBUSDT",
    "pol": "https://www.binance.com/en/trade/POLUSDT",
    "ftm": "https://www.binance.com/en/trade/SUSDT",
    "xmr": "https://www.binance.com/en/price/monero/USD",
}
usdt_link = {
    "nobitex_150": "https://nobitex.ir/panel/exchange/usdt-irt/",
    "nobitex_5000": "https://nobitex.ir/panel/exchange/usdt-irt/",
    "wallex": "https://wallex.ir/",
    "bitpin": "https://bitpin.ir/",
    "ramzinex": "https://ramzinex.com/",
}


def to_str(price):
    price = str(price)
    price = price.replace(",", "")
    price = price.replace("$", "")
    if price == "خطا" or price is None or not price:
        return "خطا"
    elif "." in price:
        return float(price)
    else:
        return f"{int(price):,}"


def get_text(the_dict):
    usd_txt, usdt_txt, gold_txt, ethgas_txt, crypto_txt = ["" for i in range(5)]

    for key, value in the_dict.items():
        if key == "currency_rates":
            for currency, data in value.items():
                if currency == "usd":
                    usd_txt += "دلار (USD)"
                    for k1, v1 in data.items():
                        # sedaghat sabze tehran bonbast tgju combination
                        if k1 == "sedaghat":
                            usd_txt += f"\nصداقت: {v1['buy']} | {v1['sell']}"
                        elif k1 == "sabze":
                            usd_txt += f"\n[سبزه](https://t.me/tahran_sabza): {v1['buy']} | {v1['sell']}"
                        elif k1 == "tehran":
                            usd_txt += f"\n[تهران](https://t.me/dollar_tehran3bze): {v1['buy']} | {v1['sell']}"
                        elif k1 == "combination":
                            usd_txt += f"\n[سبزه](https://t.me/tahran_sabza) | [تهران]((https://t.me/dollar_tehran3bze)): {v1['buy']} | {v1['sell']}"
                        elif k1 == "fardayie":
                            usd_txt += f"\nفردایی سبزه و تهران: {v1['sabze']['buy']} | {v1['sabze']['sell']}"
                        elif k1 == "naghdi":
                            usd_txt += f"\nنقدی سبزه و تهران: {v1['sabze']['buy']} | {v1['sabze']['sell']}"
                        elif k1 == "bonbast":
                            usd_txt += f"\n[بن‌بست](https://www.bonbast.com): {v1['buy']} | {v1['sell']}"
                        elif k1 == "tgju":
                            usd_txt += f"\n[سایت tgju (آزاد)](https://www.tgju.org/قیمت-دلار): {v1['price']}"
                elif currency == "usdt":
                    usdt_txt += "USDT (تتر)"
                    for k1, v1 in data.items():
                        usdt_txt += f"\n[{k1.capitalize()}]({usdt_link[k1]}): {to_str(v1['bid'])}|{to_str(v1['ask'])}"
        elif key == "gold_prices":
            gold_txt += f"طلا (GOLD) (بر اساس tala.ir)"
            gold_link = "https://www.tala.ir/gold-price"
            for name, v in value["tala.ir"].items():
                if name == "ounce":
                    gold_txt += (
                        f"\n[{gold_dict[name]}]({gold_link}): {to_str(v['price'])}$"
                    )
                else:
                    gold_txt += (
                        f"\n[{gold_dict[name]}]({gold_link}): {to_str(v['price'])}"
                    )
        elif key == "crypto":
            for coin, v in value.items():
                if coin == "eth_gas" and v:
                    ethgas_txt += "Ethereum Gas"
                    v = [str(i) for i in v]
                    ethgas_txt += f"\n[Etherscan](https://etherscan.io/gastracker): {' | '.join(v)}"
                else:
                    if not crypto_txt:
                        crypto_txt += "رمز ارز (Cryptocurrency)"
                    crypto_txt += f"\n[{coin_dict[coin]}]({coin_link[coin]}): {to_str(v['price'])}$"
    if usd_txt and ethgas_txt:
        return f"{usd_txt}\n\n\n{usdt_txt}\n\n\n{gold_txt}\n\n\n{ethgas_txt}\n\n\n{crypto_txt}"
    elif usd_txt:
        return f"{usd_txt}\n\n\n{usdt_txt}\n\n\n{gold_txt}\n\n\n{crypto_txt}"
    elif ethgas_txt:
        return f"{usdt_txt}\n\n\n{gold_txt}\n\n\n{ethgas_txt}\n\n\n{crypto_txt}"
    else:
        return f"{usdt_txt}\n\n\n{gold_txt}\n\n\n{crypto_txt}"
