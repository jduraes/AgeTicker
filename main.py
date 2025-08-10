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

DATE_PROMPT = "Date of birth (dd/mm/yyyy)"
TIME_PROMPT = "Time of birth (hh:mm:ss.ms)"

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


def _masked_edit(stdscr, y: int, x: int, label: str, mask: str, default_text: Optional[str]) -> Optional[str]:
    # mask e.g. "dd/mm/yyyy" or "hh:mm:ss.ms"
    digits_positions = [i for i, ch in enumerate(mask) if ch in ('d', 'm', 'y', 'h', 's') or ch == '0']
    # Build a char array initialized from default if provided
    buf = list(mask)
    if default_text:
        # Fill digits from default_text where digits
        dt_idx = 0
        for i, ch in enumerate(mask):
            if ch in ('d', 'm', 'y', 'h', 's') or ch == '0':
                while dt_idx < len(default_text) and not default_text[dt_idx].isdigit():
                    dt_idx += 1
                if dt_idx < len(default_text) and default_text[dt_idx].isdigit():
                    buf[i] = default_text[dt_idx]
                    dt_idx += 1
                else:
                    buf[i] = '_'
            else:
                buf[i] = ch
    else:
        buf = [ch if not (ch in ('d', 'm', 'y', 'h', 's') or ch == '0') else '_' for ch in mask]

    # caret at first digit position
    pos_list = [i for i, ch in enumerate(mask) if ch not in ['/', ':', '.', ' ']]
    # But we only accept digits where underscores are
    digit_positions = [i for i, ch in enumerate(buf) if ch == '_' or buf[i].isdigit() and mask[i] not in ['/', ':', '.', ' ']]
    # Simplify: accept digits at positions where mask had placeholders
    digit_positions = [i for i, ch in enumerate(mask) if ch in ('d', 'm', 'y', 'h', 's') or ch == '0']

    cur = 0
    while cur < len(digit_positions) and buf[digit_positions[cur]].isdigit():
        cur += 1

    curses.curs_set(1)
    stdscr.nodelay(False)

    while True:
        stdscr.move(y, x)
        stdscr.clrtoeol()
        stdscr.addstr(y, x, f"{label}: ")
        stdscr.addstr(y, x + len(label) + 2, ''.join(buf))
        # place cursor
        if digit_positions:
            stdscr.move(y, x + len(label) + 2 + digit_positions[cur if cur < len(digit_positions) else len(digit_positions)-1])
        stdscr.refresh()

        k = stdscr.get_wch()
        if isinstance(k, str) and k == '\n':
            # If any underscores remain, treat as empty
            text = ''.join(buf)
            if '_' in text:
                return None  # signal skipped/empty
            return text
        if k in (curses.KEY_BACKSPACE, 127, 8):
            if cur > 0:
                cur -= 1
                idx = digit_positions[cur]
                buf[idx] = '_'
        elif isinstance(k, str) and k.isdigit():
            if cur < len(digit_positions):
                idx = digit_positions[cur]
                buf[idx] = k
                cur += 1
        elif k == curses.KEY_LEFT:
            if cur > 0:
                cur -= 1
        elif k == curses.KEY_RIGHT:
            if cur < len(digit_positions):
                cur += 1
        elif isinstance(k, str) and k.lower() == '\x1b':  # ESC cancels
            return ''.join(buf).replace('_', '')  # allow partial? we'll handle outside
        # ignore other keys


def prompt_input(pre: Optional[DOB], stdscr) -> DOB:
    # Build defaults
    default_date = f"{pre.day:02d}/{pre.month:02d}/{pre.year:04d}" if pre else None
    default_time = f"{pre.hour:02d}:{pre.minute:02d}:{pre.second:02d}.{pre.millisecond:03d}" if pre else None

    # Draw simple prompts using masked editor
    stdscr.erase()
    stdscr.addstr(0, 2, "Enter details. Press Enter to accept. ESC to abort.")

    # Date input
    while True:
        date_text = _masked_edit(stdscr, 2, 2, DATE_PROMPT, "dd/mm/yyyy", default_date)
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
        time_text = _masked_edit(stdscr, 5, 2, TIME_PROMPT, "hh:mm:ss.ms", default_time)
        if time_text is None:
            if default_time:
                time_text = default_time
            else:
                # Noon default if skipped
                hour, minute, second, ms = 12, 0, 0, 0
                return DOB(day, month, year, hour, minute, second, ms)
        tm = TIME_RE.match(time_text)
        if not tm:
            stdscr.addstr(6, 2, "Invalid time. Use hh:mm:ss.ms.")
            stdscr.refresh()
            curses.napms(800)
            stdscr.move(6, 2)
            stdscr.clrtoeol()
            continue
        hour, minute, second, ms = map(int, tm.groups())
        if not (0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59 and 0 <= ms <= 999):
            stdscr.addstr(6, 2, "Time out of range.")
            stdscr.refresh()
            curses.napms(800)
            stdscr.move(6, 2)
            stdscr.clrtoeol()
            continue
        try:
            _ = dt.datetime(year, month, day, hour, minute, second, ms * 1000)
            return DOB(day, month, year, hour, minute, second, ms)
        except ValueError:
            stdscr.addstr(6, 2, "Invalid date/time combination.")
            stdscr.refresh()
            curses.napms(800)
            stdscr.move(6, 2)
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
        now = dt.datetime.now()
        y, mo, d, h, mi, s, ms = diff_ymdhmsms(dob_dt, now)

        # Zero-padded display widths
        years_txt = f"{y:03d}"
        months_txt = f"{mo:02d}"
        days_txt = f"{d:02d}"
        hours_txt = f"{h:02d}"
        minutes_txt = f"{mi:02d}"
        seconds_txt = f"{s:02d}"
        ms_txt = f"{ms:03d}"

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
            ("MSEC", ms_txt),
        ]

        band_height = 1 + 5 + 1  # label + big 5 rows + spacer
        max_band_bottom = base_row

        # Clear previous band area minimally by overwriting spaces where needed is complex; we just redraw over
        last_render_lines = []
        last_labels_positions = []

        for label, value in entries:
            big_rows = render_big(value)
            # Width of this block
            block_w = max(len(r) for r in big_rows)
            label_w = len(label)
            block_w = max(block_w, label_w)

            # Wrap if needed
            if cur_x + block_w > max_x - 2:
                # move to next band
                base_row = max_band_bottom + 1
                cur_x = 2

            # Draw label
            safe_addstr(base_row, cur_x, label)
            last_labels_positions.append((base_row, cur_x, label))
            # Draw big rows
            for i, row in enumerate(big_rows):
                safe_addstr(base_row + 1 + i, cur_x, row)
            # Capture last render lines by reconstructing block rows
            for i, row in enumerate(big_rows):
                # ensure list is large enough
                line_index = base_row + 1 + i
                while len(last_render_lines) <= line_index:
                    last_render_lines.append("")
                # naive: place row at x; for final print we will just print combined sections sequentially instead
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
            ms_txt = f"{ms:03d}"
            entries = [
                ("YEARS", years_txt),
                ("MONTHS", months_txt),
                ("DAYS", days_txt),
                ("HOURS", hours_txt),
                ("MINUTES", minutes_txt),
                ("SECONDS", seconds_txt),
                ("MSEC", ms_txt),
            ]
            # Compose a simple horizontal snapshot for stdout
            labels = '   '.join(label for label, _ in entries)
            big_rows_per = [render_big(val) for _, val in entries]
            rows_out = []
            for i in range(5):
                row = '   '.join(br[i] for br in big_rows_per)
                rows_out.append(row)
            print("Age ticker (final snapshot)")
            print(labels)
            for r in rows_out:
                print(r)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass

