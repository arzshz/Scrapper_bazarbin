import datetime
from datetime import datetime as dt

import jdatetime
import pytz
from dateutil.relativedelta import relativedelta

tehran_tz = pytz.timezone("Asia/Tehran")


def parse_date(date_str: str) -> datetime.date:
    date_str = persian_to_english(date_str.strip())
    date_str = date_str.replace(" ", "")
    year, month, day = None, None, None
    relative_date = ["Y", "M", "D", "NOW"]
    for d in relative_date:
        if d in date_str or date_str == "0":
            year, month, day = parse_relative_date(date_str)
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
        jdate = jdatetime.date(year, month, day).togregorian()
        return jdate
    elif 2014 < year < 2045 and 0 < month < 13 and 0 < day < 32:
        date_obj = dt(year, month, day).date()
        return date_obj
    else:
        raise ValueError("❌ Invalid date format.")


def persian_to_english(text):
    """Convert Persian/Farsi numbers to English"""
    persian_numbers = "۰۱۲۳۴۵۶۷۸۹"
    english_numbers = "0123456789"
    translation_table = str.maketrans(persian_numbers, english_numbers)
    return text.translate(translation_table)


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
    years, months, days = get_date(s)
    if years != 0 or months != 0 or days != 0:
        delta = relativedelta(years=years, months=months, days=days)
        target = now + delta
        return target.year, target.month, target.day
    else:
        raise ValueError("❌ Invalid date format.")


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
                f"❌ Ambiguous date. Please use separators such as YYYY-MM-DD or YYYY/MM/DD."
            )
    elif len(month_day) == 2:  # MD
        month = int(month_day[0])
        day = int(month_day[1])
    else:
        raise ValueError(f"❌ Invalid date format.")

    return month, day


def get_date(s: str):
    num = ""
    years = months = days = 0
    for ch in s:
        if ch in ["-", "+"]:
            num += ch
        elif ch.isdigit():
            num += ch
        else:
            if not num or num in ["-", "+"]:
                continue
            value = int(num)
            if ch == "Y":
                years += value
            elif ch == "M":
                months += value
            elif ch == "D":
                days += value
            num = ""  # reset
    return years, months, days


def parse_date_and_time(input_str: str) -> datetime.datetime:
    """
    Parse a string combining date and time into a datetime object.

    Supported formats:
      - Date formats: YYYYMMDD, YYYY/MM/DD, YYYY-MM-DD, YYYY MM DD, -XY-YM-ZD
      - Time formats: HH:MM, HHMM, HH MM, -Xh-Ym, -Xh -Ym
      - Combined: date followed by time, separated by space
      - Time only: just the time part (uses today's date)

    Examples:
      - "14040819 12:35"
      - "1404/08/19 -2h-10m"
      - "-1Y-2M-3D 12:35"
      - "12:35"
      - "-2h-10m"
    """
    input_str = persian_to_english(input_str.strip())

    # Split by spaces to separate date and time parts
    parts = input_str.split()

    # Check if input is time-only
    if len(parts) == 1 and parts[0] in ["0", "NOW"]:
        return dt.now(tehran_tz)
    elif len(parts) == 1 and is_time(parts[0]):
        # Time only - use today's date
        return parse_time(input_str)
    elif len(parts) == 2 and is_time(" ".join(parts)):
        # It's time-only like "12 35"
        return parse_time(" ".join(parts))

    # Not time-only, so parse as date + time
    date_part = parts[0]
    time_part = " ".join(parts[1:])
    now = dt.now(tehran_tz)

    date_obj = parse_date(date_part)
    date_obj = dt.combine(date_obj, now.time())

    if time_part:
        time_obj = parse_time(time_part)
        is_relative = is_relative_time(time_part)
        if is_relative:
            delta = relativedelta(time_obj, now)
            result = date_obj + delta
        else:
            result = date_obj.replace(
                hour=time_obj.hour, minute=time_obj.minute, second=0, microsecond=0
            )
    else:
        result = date_obj.replace(hour=0, minute=0, second=0, microsecond=0)

    # Add Tehran timezone
    result = tehran_tz.localize(result)

    return result


def is_time(s: str) -> bool:
    # must not contain any other alphabetic characters
    for ch in s:
        if ch.isalpha() and ch not in ("h", "m"):
            return False

    parts = s.split()
    if len(parts) == 1 and ("h" in parts[0] or "m" in parts[0]):
        return True
    elif len(parts) == 2 and ("h" in parts[0] or "m" in parts[0]):
        return True

    if ":" in s and len(s.strip()) < 6:
        try:
            hours, minutes = map(int, s.split(":"))
            return True
        except ValueError:
            return False

    if len(s.replace(" ", "").strip()) < 5 and s.replace(" ", "").isdigit():
        return True
    return False


def parse_time(time_str: str) -> dt:
    """
    Parse time string and return datetime.time object.
    Supports formats:
      - HH:MM (e.g., "12:35")
      - HHMM (e.g., "1235")
      - HH MM (e.g., "12 35")
      - -Xh-Ym (relative time, e.g., "-2h-10m")
      - -Xh -Ym (relative time with space, e.g., "-2h -10m")
    """
    time_str = persian_to_english(time_str.strip())
    hours = minutes = is_relative = dt_object = None

    relative_date = ["h", "m"]
    for d in relative_date:
        if d in time_str:
            dt_object = parse_relative_time(time_str)
            hours, minutes, is_relative = dt_object.hour, dt_object.minute, True
            break
    if not (hours or minutes):
        sep = [":", " "]
        for s in sep:
            if s in time_str:
                try:
                    hours, minutes = map(int, time_str.split(s))
                    is_digit = "N"
                except ValueError:
                    raise ValueError("❌ Invalid time format.")
                break
        else:
            is_digit = "T" if time_str.isdigit() else "F"

        if is_digit == "F" or (is_digit == "T" and len(time_str) > 5):
            raise ValueError("❌ Invalid time format.")
        elif is_digit == "T":
            hours, minutes = parse_hour_minute(time_str)

    if (
        hours is not None
        and minutes is not None
        and 0 <= hours <= 24
        and 0 <= minutes <= 59
    ):
        if is_relative:
            return dt_object
        return dt.now(tehran_tz).replace(hour=hours, minute=minutes)
    else:
        raise ValueError("❌ Invalid time format.")


def is_relative_time(time_str):
    relative_str = ["h", "m"]
    for d in relative_str:
        if d in time_str:
            parse_relative_time(time_str)
            return True
    return False


def parse_relative_time(s: str):
    """
    Parse a string like '-3h-5m' or '-3h+10m' into (hours, minutes) in Tehran timezone.
    Units:
      h = hours, m = minutes
    """
    hours, minutes = get_time(s)
    if hours != 0 or minutes != 0:
        # Get current time in Tehran timezone
        now = dt.now(tehran_tz)
        delta = relativedelta(hours=hours, minutes=minutes)
        target = now + delta
        return target
    else:
        raise ValueError("❌ Invalid time format.")


def parse_hour_minute(time_str: str):
    if len(time_str) == 4:
        hour = int(time_str[:2])
        minute = int(time_str[2:])
    elif len(time_str) == 3:
        # Could be hhm or hmm → ambiguous if both interpretations are valid
        h1, m1 = int(time_str[:2]), int(time_str[2:])  # hhm
        h2, m2 = int(time_str[0]), int(time_str[1:])  # hmm

        valid_hhm = 0 <= h1 <= 24 and 0 <= m1 <= 59
        valid_hmm = 0 <= h2 <= 24 and 0 <= m2 <= 59

        if valid_hhm and not valid_hmm:
            hour, minute = h1, m1
        elif valid_hmm and not valid_hhm:
            hour, minute = h2, m2
        elif (h1, m1) == (h2, m2):
            hour, minute = h1, m1
        else:
            raise ValueError(
                f"❌ Ambiguous time. Please use a ':' separator (e.g., 12:35)."
            )
    elif 0 <= int(time_str) <= 24:
        hour, minute = int(time_str), 0
    else:
        raise ValueError(f"❌ Invalid time format.")
    return hour, minute


def get_time(s: str):
    s = s.replace(" ", "")
    hours = minutes = 0
    num = ""
    for ch in s:
        if ch in ["-", "+"]:
            num += ch
        elif ch.isdigit():
            num += ch
        else:
            if num and num not in ["-", "+"]:
                value = int(num)
                if ch == "h":
                    hours += value
                elif ch == "m":
                    minutes += value
            num = ""  # reset
    return hours, minutes
