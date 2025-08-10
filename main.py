#!/usr/bin/env python3

import curses
import datetime as dt
import json
import os
import re
from dataclasses import dataclass
from typing import Optional, Tuple, List

# 8.3-friendly filename as per user's rule
LAST_FILE = "lastdob.txt"

DATE_PROMPT = "Enter date of birth [dd/mm/yyyy]"
TIME_PROMPT = "Enter time of birth [hh:mm:ss.ms] (press Enter to skip)"

# Strict formats: dd/mm/yyyy and hh:mm:ss.ms
DATE_RE = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")
TIME_RE = re.compile(r"^(\d{2}):(\d{2}):(\d{2})\.(\d{3})$")


@dataclass
class DOB:
    day: int
    month: int
    year: int
    hour: int
    minute: int
    second: int
    millisecond: int

    def to_datetime(self) -> dt.datetime:
        micro = self.millisecond * 1000
        return dt.datetime(self.year, self.month, self.day, self.hour, self.minute, self.second, micro)

    @staticmethod
    def from_datetime(d: dt.datetime) -> "DOB":
        ms = d.microsecond // 1000
        return DOB(d.day, d.month, d.year, d.hour, d.minute, d.second, ms)

    def serialize(self) -> str:
        # Two lines: date and time. Friendly for manual editing.
        date_s = f"{self.day:02d}/{self.month:02d}/{self.year:04d}"
        time_s = f"{self.hour:02d}:{self.minute:02d}:{self.second:02d}.{self.millisecond:03d}"
        return date_s + "\n" + time_s + "\n"

    @staticmethod
    def deserialize(text: str) -> Optional["DOB"]:
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if not lines:
            return None
        date_s = lines[0]
        time_s = lines[1] if len(lines) > 1 else ""
        date_m = DATE_RE.match(date_s)
        if not date_m:
            return None
        d, m, y = map(int, date_m.groups())
        if time_s:
            tm = TIME_RE.match(time_s)
            if not tm:
                # Backward-compat: accept old format with colon between sec and ms
                tm_old = re.match(r"^(\d{1,2}):(\d{1,2}):(\d{1,2}):(\d{1,3})$", time_s)
                if not tm_old:
                    return None
                hh, mm, ss, ms = map(int, tm_old.groups())
            else:
                hh, mm, ss, ms = map(int, tm.groups())
        else:
            # No time provided in file; default to noon
            hh = 12
            mm = 0
            ss = 0
            ms = 0
        try:
            # Validate by constructing
            _ = dt.datetime(y, m, d, hh, mm, ss, ms * 1000)
        except ValueError:
            return None
        return DOB(d, m, y, hh, mm, ss, ms)


def load_last_dob(path: str) -> Optional[DOB]:
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = f.read()
        return DOB.deserialize(data)
    except Exception:
        return None


def save_last_dob(path: str, dob: DOB) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(dob.serialize())
    except Exception:
        pass


def prompt_input(pre: Optional[DOB]) -> DOB:
    # Date section (loop until valid date only)
    default_date = f"{pre.day:02d}/{pre.month:02d}/{pre.year:04d}" if pre else None
    while True:
        prompt = DATE_PROMPT + " (two-digit day/month, four-digit year, e.g., 07/09/1985)"
        if default_date:
            prompt += f" [{default_date}]"
        prompt += ": "
        s = input(prompt).strip()
        if not s and default_date:
            s = default_date
        m = DATE_RE.match(s)
        if not m:
            print("Invalid date format. Use dd/mm/yyyy with two-digit day/month and 4-digit year (e.g., 07/09/1985).")
            continue
        day, month, year = map(int, m.groups())
        # Validate calendar date
        try:
            _ = dt.datetime(year, month, day)
        except ValueError:
            print("Invalid calendar date. Please enter a real date (e.g., 29/02 only on leap years).")
            continue
        break

    # Time section (loop only on time errors; do not re-ask date)
    default_time = f"{pre.hour:02d}:{pre.minute:02d}:{pre.second:02d}.{pre.millisecond:03d}" if pre else None
    while True:
        tprompt = TIME_PROMPT + " (two-digit hh/mm/ss and three-digit ms; e.g., 04:05:06.007)"
        if default_time:
            tprompt += f" [{default_time}]"
        tprompt += ": "
        ts = input(tprompt).strip()
        if not ts:
            if default_time:
                ts = default_time
            else:
                # Assume mid-day sharp
                hour = 12
                minute = 0
                second = 0
                ms = 0
                try:
                    _ = dt.datetime(year, month, day, hour, minute, second, ms * 1000)
                    return DOB(day, month, year, hour, minute, second, ms)
                except ValueError as e:
                    print(f"Invalid date/time: {e}")
                    continue
        tm = TIME_RE.match(ts)
        if not tm:
            print("Invalid time format. Use hh:mm:ss.ms with two-digit hh/mm/ss and three-digit ms (e.g., 04:05:06.007).")
            continue
        hour, minute, second, ms = map(int, tm.groups())
        # Range checks
        if not (0 <= hour <= 23):
            print("Hour must be between 00 and 23.")
            continue
        if not (0 <= minute <= 59):
            print("Minute must be between 00 and 59.")
            continue
        if not (0 <= second <= 59):
            print("Second must be between 00 and 59.")
            continue
        if not (0 <= ms <= 999):
            print("Milliseconds must be between 000 and 999.")
            continue
        try:
            _ = dt.datetime(year, month, day, hour, minute, second, ms * 1000)
            return DOB(day, month, year, hour, minute, second, ms)
        except ValueError as e:
            print(f"Invalid date/time: {e}")
            continue


# Big ASCII digits (5 rows high) for 0-9 and some separators
BIG_FONT = {
    '0': [
        " ███ ",
        "█   █",
        "█   █",
        "█   █",
        " ███ ",
    ],
    '1': [
        "  █  ",
        " ██  ",
        "  █  ",
        "  █  ",
        " ███ ",
    ],
    '2': [
        " ███ ",
        "█   █",
        "   █ ",
        "  █  ",
        "█████",
    ],
    '3': [
        "████ ",
        "    █",
        " ███ ",
        "    █",
        "████ ",
    ],
    '4': [
        "█  █ ",
        "█  █ ",
        "█████",
        "   █ ",
        "   █ ",
    ],
    '5': [
        "█████",
        "█    ",
        "████ ",
        "    █",
        "████ ",
    ],
    '6': [
        " ███ ",
        "█    ",
        "████ ",
        "█   █",
        " ███ ",
    ],
    '7': [
        "█████",
        "   █ ",
        "  █  ",
        " █   ",
        " █   ",
    ],
    '8': [
        " ███ ",
        "█   █",
        " ███ ",
        "█   █",
        " ███ ",
    ],
    '9': [
        " ███ ",
        "█   █",
        " ████",
        "    █",
        " ███ ",
    ],
    ':': [
        "     ",
        "  █  ",
        "     ",
        "  █  ",
        "     ",
    ],
    '.': [
        "     ",
        "     ",
        "     ",
        "  █  ",
        "     ",
    ],
}


def render_big(text: str) -> List[str]:
    rows = ["" for _ in range(5)]
    for idx, ch in enumerate(text):
        glyph = BIG_FONT.get(ch)
        if glyph is None:
            glyph = ["     "] * 5
        # inter-char spacing
        spacer = " "
        for i in range(5):
            rows[i] += glyph[i]
            if idx != len(text) - 1:
                rows[i] += spacer
    return rows


def add_year_month_from(dt0: dt.datetime, years: int = 0, months: int = 0) -> dt.datetime:
    y = dt0.year + years
    m = dt0.month + months
    # normalize months
    y += (m - 1) // 12
    m = (m - 1) % 12 + 1
    # clamp day to end of month
    import calendar
    last_day = calendar.monthrange(y, m)[1]
    d = min(dt0.day, last_day)
    return dt.datetime(y, m, d, dt0.hour, dt0.minute, dt0.second, dt0.microsecond)


def diff_ymdhmsms(start: dt.datetime, now: dt.datetime) -> Tuple[int, int, int, int, int, int, int]:
    # Compute years and months by stepping, then remaining via timedelta
    # Years
    lo, hi = 0, 300  # bounds
    while add_year_month_from(start, years=hi) <= now:
        lo = hi
        hi *= 2
    # binary search years
    yl, yr = lo, hi
    while yl < yr:
        mid = (yl + yr + 1) // 2
        if add_year_month_from(start, years=mid) <= now:
            yl = mid
        else:
            yr = mid - 1
    years = yl
    anchor = add_year_month_from(start, years=years)

    # Months 0..11
    ml, mr = 0, 11
    while ml < mr:
        mid = (ml + mr + 1) // 2
        if add_year_month_from(anchor, months=mid) <= now:
            ml = mid
        else:
            mr = mid - 1
    months = ml
    anchor2 = add_year_month_from(anchor, months=months)

    delta = now - anchor2
    days = delta.days
    rem_us = delta.seconds * 1_000_000 + delta.microseconds
    hours, rem_us = divmod(rem_us, 3_600_000_000)
    minutes, rem_us = divmod(rem_us, 60_000_000)
    seconds, rem_us = divmod(rem_us, 1_000_000)
    ms = rem_us // 1000

    return years, months, days, hours, minutes, seconds, ms


def draw_screen(stdscr, dob_dt: dt.datetime):
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(20)  # 20ms

    while True:
        now = dt.datetime.now()
        y, mo, d, h, mi, s, ms = diff_ymdhmsms(dob_dt, now)

        stdscr.erase()
        title = "Age ticker (press ESC to quit)"
        stdscr.addstr(0, 2, title)

        # Compose big displays per unit
        line = 2
        entries = [
            ("YEARS", f"{y}"),
            ("MONTHS", f"{mo}"),
            ("DAYS", f"{d}"),
            ("HOURS", f"{h:02d}"),
            ("MINUTES", f"{mi:02d}"),
            ("SECONDS", f"{s:02d}"),
            ("MILLISECONDS", f"{ms:03d}"),
        ]
        for label, value in entries:
            stdscr.addstr(line, 2, label)
            big = render_big(value)
            for i, row in enumerate(big):
                stdscr.addstr(line + 1 + i, 2, row)
            line += 1 + len(big) + 1

        stdscr.refresh()

        # Handle ESC
        try:
            ch = stdscr.getch()
        except Exception:
            ch = -1
        if ch == 27:
            break


def main():
    pre = load_last_dob(LAST_FILE)
    dob = prompt_input(pre)
    # Persist selection immediately
    save_last_dob(LAST_FILE, dob)

    dob_dt = dob.to_datetime()

    curses.wrapper(draw_screen, dob_dt)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass

