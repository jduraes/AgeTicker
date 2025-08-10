# AgeTicker: ASCII Age Ticker

This is a simple Python curses application that displays, in ASCII big digits, the elapsed time since a person's date of birth, broken down into years, months, days, hours, minutes, and seconds. It runs as a live ticker until ESC is pressed.

Features
- Prompts for date and time of birth in two sections.
  - Date: dd/mm/yyyy (required; two-digit day/month and four-digit year)
  - Time: hh:mm:ss (optional; press Enter to skip)
- If time is skipped and there is no saved value, assumes 12:00:00 (noon sharp).
- Saves last-entered DOB into an 8.3-friendly file name `lastdob.txt` and pre-populates prompts next run.
  - If a saved value exists, pressing Enter at the prompts uses the saved value.
- Curses-based ticker shows big ASCII numbers for each unit in a horizontal layout (with wrapping when needed) and updates in near real-time.
- Quit with ESC.

Install
- Requires Python 3.8+
- On macOS, Python’s built-in `curses` is available in the system Python; for Homebrew Python, ensure `_curses` is installed (usually default).

Run
- From source (requires Python 3.8+):

  python3 main.py

- Prebuilt binaries (macOS, Windows, Linux):
  - See Releases for downloads. Make the file executable if needed (macOS/Linux):

    chmod +x ./ageticker-<platform>
    ./ageticker-<platform>

Usage notes
- Input formats:
  - Date: dd/mm/yyyy (e.g., 07/09/1985)
  - Time: hh:mm:ss (e.g., 14:23:45)
- On first run (no saved value):
  - If you press Enter at the time prompt, it uses 12:00:00.
- On subsequent runs (with saved value present):
  - The prompts show the previously saved values in brackets.
  - Pressing Enter accepts those values.

Persistence file
- The app reads and writes `lastdob.txt` in the working directory.
- Format:
  - Line 1: dd/mm/yyyy
  - Line 2: hh:mm:ss

Implementation notes
- The difference in years and months is computed by searching for the maximum full years and months that fit between DOB and now, then the remainder is split into days, hours, minutes, and seconds.
- The ASCII big font is 5 rows tall and rendered per unit with labels.

Known limitations
- Terminal window needs to be tall enough to display all sections. If too small, content may scroll or clip.
- The app expects Gregorian calendar dates; localized calendars aren’t supported.

Screenshot
- Placeholder image below; replace with a real screenshot or GIF:

  ![AgeTicker screenshot](docs/screenshot.png)

Homebrew (macOS)
- Tap and install:

  brew tap jduraes/ageticker https://github.com/jduraes/homebrew-ageticker
  brew install ageticker

License
- Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0). See LICENSE.

