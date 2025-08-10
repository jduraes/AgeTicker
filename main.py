#!/usr/bin/env python3

import argparse
import curses
import datetime as dt
import json
import os
import re
from dataclasses import dataclass
from typing import Optional, Tuple, List

# 8.3-friendly filename as per user's rule
LAST_FILE = "lastdob.txt"

# App version (keep in sync with tags/releases)
VERSION = "0.1.2"

DATE_PROMPT = "Date of birth (dd/mm/yyyy)"
TIME_PROMPT = "Time of birth (hh:mm:ss)"

# Strict formats: dd/mm/yyyy and hh:mm:ss
DATE_RE = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")
TIME_RE = re.compile(r"^(\d{2}):(\d{2}):(\d{2})$")


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
        time_s = f"{self.hour:02d}:{self.minute:02d}:{self.second:02d}"
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
            if tm:
                hh, mm, ss = map(int, tm.groups())
                ms = 0
            else:
                # Backward-compat: accept old formats with ms
                tm_dot = re.match(r"^(\d{1,2}):(\d{1,2}):(\d{1,2})\.(\d{1,3})$", time_s)
                tm_col = re.match(r"^(\d{1,2}):(\d{1,2}):(\d{1,2}):(\d{1,3})$", time_s)
                use = tm_dot or tm_col
                if not use:
                    return None
                hh, mm, ss, ms = map(int, use.groups())
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


def _masked_edit(stdscr, y: int, x: int, label: str, mask: str, default_text: Optional[str]) -> Optional[str]:
    # Build buffer with separators and underscores
    buf = [ch if ch in ['/', ':', '.', ' '] else '_' for ch in mask]
    digit_positions = [i for i, ch in enumerate(mask) if ch not in ['/', ':', '.', ' ']]
    cur = 0
    edited = False

    curses.curs_set(1)
    stdscr.nodelay(False)

    while True:
        stdscr.move(y, x)
        stdscr.clrtoeol()
        hint = f"{label}: "
        if default_text:
            hint += f"[{default_text}] "
        stdscr.addstr(y, x, hint)
        stdscr.addstr(y, x + len(hint), ''.join(buf))
        # place cursor
        if digit_positions:
            stdscr.move(y, x + len(hint) + digit_positions[cur if cur < len(digit_positions) else len(digit_positions)-1])
        stdscr.refresh()

        k = stdscr.get_wch()
        if isinstance(k, str) and k == '\n':
            text = ''.join(buf)
            if '_' in text:
                if not edited and default_text:
                    return default_text
                # incomplete and no default accepted -> continue editing
                continue
            return text
        # macOS backspace often arrives as '\x7f' or '\x08'
        if (k == curses.KEY_BACKSPACE) or (isinstance(k, str) and k in ('\x7f', '\x08')) or (not isinstance(k, str) and k in (127, 8)):
            # Backspace: clear previous digit and move left
            if cur > 0:
                cur -= 1
                idx = digit_positions[cur]
                buf[idx] = '_'
                edited = True
        elif k == curses.KEY_DC or (isinstance(k, str) and k == '\x1b[3~'):
            # Delete (forward): clear current digit but do not move cursor
            if cur < len(digit_positions):
                idx = digit_positions[cur]
                buf[idx] = '_'
                edited = True
        elif isinstance(k, str) and k.isdigit():
            if cur < len(digit_positions):
                idx = digit_positions[cur]
                buf[idx] = k
                cur += 1
                edited = True
        elif k == curses.KEY_LEFT:
            if cur > 0:
                cur -= 1
        elif k == curses.KEY_RIGHT:
            if cur < len(digit_positions):
                cur += 1
        elif isinstance(k, str) and k.lower() == '\x1b':  # ESC cancels
            return default_text if default_text else None
        # ignore other keys


def prompt_input(pre: Optional[DOB], stdscr) -> DOB:
    # Build defaults
    default_date = f"{pre.day:02d}/{pre.month:02d}/{pre.year:04d}" if pre else None
    default_time = f"{pre.hour:02d}:{pre.minute:02d}:{pre.second:02d}" if pre else None

    # Draw simple prompts using masked editor
    stdscr.erase()
    stdscr.addstr(0, 2, f"AgeTicker v{VERSION}")
    stdscr.addstr(1, 2, "")
    stdscr.addstr(2, 2, "Enter details. Press Enter to accept. ESC to abort.")
    stdscr.refresh()

    # Date input
    while True:
        date_text = _masked_edit(stdscr, 4, 2, DATE_PROMPT, "dd/mm/yyyy", default_date)
        if date_text is None:
            # user pressed enter with incomplete -> if default exists use it, else re-ask
            if default_date:
                date_text = default_date
            else:
                continue
        m = DATE_RE.match(date_text)
        if not m:
            # show brief error and retry
            stdscr.addstr(3, 2, "Invalid date. Use dd/mm/yyyy.")
            stdscr.refresh()
            curses.napms(800)
            stdscr.move(3, 2)
            stdscr.clrtoeol()
            continue
        day, month, year = map(int, m.groups())
        try:
            _ = dt.datetime(year, month, day)
            break
        except ValueError:
            stdscr.addstr(3, 2, "Invalid calendar date.")
            stdscr.refresh()
            curses.napms(800)
            stdscr.move(3, 2)
            stdscr.clrtoeol()
            continue

    # Time input
    while True:
        time_text = _masked_edit(stdscr, 7, 2, TIME_PROMPT, "hh:mm:ss", default_time)
        if time_text is None:
            if default_time:
                time_text = default_time
            else:
                # Noon default if skipped
                hour, minute, second, ms = 12, 0, 0, 0
                return DOB(day, month, year, hour, minute, second, ms)
        tm = TIME_RE.match(time_text)
        if not tm:
            stdscr.addstr(8, 2, "Invalid time. Use hh:mm:ss.")
            stdscr.refresh()
            curses.napms(800)
            stdscr.move(8, 2)
            stdscr.clrtoeol()
            continue
        hour, minute, second = map(int, tm.groups())
        ms = 0
        if not (0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59):
            stdscr.addstr(8, 2, "Time out of range.")
            stdscr.refresh()
            curses.napms(800)
            stdscr.move(8, 2)
            stdscr.clrtoeol()
            continue
        try:
            _ = dt.datetime(year, month, day, hour, minute, second, ms * 1000)
            return DOB(day, month, year, hour, minute, second, ms)
        except ValueError:
            stdscr.addstr(8, 2, "Invalid date/time combination.")
            stdscr.refresh()
            curses.napms(800)
            stdscr.move(8, 2)
            stdscr.clrtoeol()
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

    def safe_addstr(y: int, x: int, s: str):
        try:
            max_y, max_x = stdscr.getmaxyx()
            if x < 0 or y < 0 or y >= max_y:
                return
            if x >= max_x:
                return
            if len(s) > max_x - x:
                s = s[: max_x - x]
            stdscr.addstr(y, x, s)
        except Exception:
            pass

    last_render_lines: List[str] = []
    last_labels_positions: List[Tuple[int, int, str]] = []

    while True:
        stdscr.erase()
        now = dt.datetime.now()
        y, mo, d, h, mi, s, ms = diff_ymdhmsms(dob_dt, now)

        # Zero-padded display widths
        years_txt = f"{y:03d}"
        months_txt = f"{mo:02d}"
        days_txt = f"{d:02d}"
        hours_txt = f"{h:02d}"
        minutes_txt = f"{mi:02d}"
        seconds_txt = f"{s:02d}"

        # draw header once at top
        safe_addstr(0, 2, "Age ticker (ESC to quit)")

        # Horizontal layout with wrapping
        base_row = 2  # label row for current band
        cur_x = 2
        gap = 4
        max_y, max_x = stdscr.getmaxyx()

        entries = [
            ("YEARS", years_txt),
            ("MONTHS", months_txt),
            ("DAYS", days_txt),
            ("HOURS", hours_txt),
            ("MINUTES", minutes_txt),
            ("SECONDS", seconds_txt),
        ]

        band_height = 1 + 5 + 1  # label + big 5 rows + spacer
        max_band_bottom = base_row

        # Clear previous band area
        last_render_lines = []
        last_labels_positions = []

        for label, value in entries:
            big_rows = render_big(value)
            # Block width based on big digit rows
            block_w = len(big_rows[0]) if big_rows else 0

            # Wrap if needed
            if cur_x + block_w > max_x - 2:
                # move to next band
                base_row = max_band_bottom + 1
                cur_x = 2

            # Center label over the block
            label_x = cur_x + max(0, (block_w - len(label)) // 2)
            safe_addstr(base_row, label_x, label)
            last_labels_positions.append((base_row, label_x, label))

            # Draw big rows
            for i, row in enumerate(big_rows):
                safe_addstr(base_row + 1 + i, cur_x, row)

            # Update x and band bottom
            cur_x += block_w + gap
            max_band_bottom = max(max_band_bottom, base_row + 1 + len(big_rows))

        stdscr.refresh()

        # Handle ESC
        try:
            ch = stdscr.getch()
        except Exception:
            ch = -1
        if ch == 27:
            break


def _run_app(stdscr):
    pre = load_last_dob(LAST_FILE)
    dob = prompt_input(pre, stdscr)
    save_last_dob(LAST_FILE, dob)
    dob_dt = dob.to_datetime()
    draw_screen(stdscr, dob_dt)


def main():
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--version", action="store_true", help="Print version and exit")
    args, _ = parser.parse_known_args()
    if args.version:
        print(f"AgeTicker v{VERSION}")
        return

    # Use curses for masked input and ticker, but on exit we will print a final snapshot
    last_lines_holder: List[str] = []
    try:
        curses.wrapper(_run_app)
    finally:
        # After curses ends, we cannot easily retrieve drawn content; instead, recompute one last snapshot and print
        pre = load_last_dob(LAST_FILE)
        if pre:
            dob_dt = pre.to_datetime()
            now = dt.datetime.now()
            y, mo, d, h, mi, s, ms = diff_ymdhmsms(dob_dt, now)
            years_txt = f"{y:03d}"
            months_txt = f"{mo:02d}"
            days_txt = f"{d:02d}"
            hours_txt = f"{h:02d}"
            minutes_txt = f"{mi:02d}"
            seconds_txt = f"{s:02d}"
            entries = [
                ("YEARS", years_txt),
                ("MONTHS", months_txt),
                ("DAYS", days_txt),
                ("HOURS", hours_txt),
                ("MINUTES", minutes_txt),
                ("SECONDS", seconds_txt),
            ]
            # Compose a simple horizontal snapshot for stdout
            big_rows_per = [render_big(val) for _, val in entries]
            # Determine block widths
            block_widths = [len(br[0]) for br in big_rows_per]
            # Build centered label line
            label_segments = []
            for (label, _), w in zip(entries, block_widths):
                pad_left = max(0, (w - len(label)) // 2)
                segment = ' ' * pad_left + label.ljust(w - pad_left)
                label_segments.append(segment)
            label_line = '   '.join(label_segments)
            # Build big rows concatenated
            rows_out = []
            for i in range(5):
                row = '   '.join(br[i] for br in big_rows_per)
                rows_out.append(row)
            print(f"AgeTicker v{VERSION}")
            print()
            print("Age ticker (final snapshot)")
            print(label_line)
            for r in rows_out:
                print(r)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass

