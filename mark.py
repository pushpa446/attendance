#!/usr/bin/env python3
"""
Samagam attendance helper (semi-automatic).

Usage:
    python mark.py 4 12 17     # Sn. 4, 12, 17 are ABSENT (everyone else stays Present)
    python mark.py             # everyone present

Flow:
  1. Opens a visible Chrome window (saved profile, so logins/Cloudflare checks persist).
  2. Logs in: if SAMAGAM_ID and SAMAGAM_PASS environment variables are set, it fills
     them in, waits for Cloudflare to say Success, and clicks Login by itself.
     Otherwise YOU log in and press Enter in the terminal.
  3. Script clicks through the menu to the attendance page (NAV_STEPS).
  4. Leaves everyone Present (portal default) and sets only the listed Sn. numbers Absent.
  5. Aborts if any Sn. number is not found. Otherwise saves and takes a screenshot.
   (No weekend or holiday check: it marks whenever you run it.)

Setup (once):
    python3 -m venv ~/attendance && source ~/attendance/bin/activate
    pip install playwright && playwright install chromium
"""
import sys
import os
import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

# ------------------------- CONFIG (edit these) -------------------------
LOGIN_URL = "https://samagam.kvs.gov.in/"

# Menu clicks after login, by visible text, in order. FILL THESE IN.
NAV_STEPS = [
    "SIS",
    "Attendance",
    "Mark Attendance",
    "View / Edit",      # button on the Class 6 Section A card
]

# Optional: direct attendance URL (leave "" if none)
ATTENDANCE_URL = ""

# Class/section selection on the attendance page (leave empty if not needed)
# Example: {"Class": "Class 5", "Section": "A"}
FILTERS = {}

# One row per student
ROW_SELECTOR = "table tbody tr"
# Element inside a row that contains the Sn. (serial number, 1st column)
ROLL_SELECTOR = "td:nth-child(1)"

# "dropdown" -> a <select> in each row; "toggle" -> buttons/labels with text
MODE = "dropdown"
PRESENT_LABEL = "Present"
ABSENT_LABEL = "Absent"
DROPDOWN_SELECTOR = "select"          # used when MODE = "dropdown"

SUBMIT_TEXT = "Save"
PROFILE_DIR = str(Path.home() / ".attendance-profile")
# -----------------------------------------------------------------------


def set_status(row, label):
    if MODE == "dropdown":
        row.locator(DROPDOWN_SELECTOR).first.select_option(label=label)
    else:
        row.get_by_text(label, exact=True).first.click()


def main():
    absent = {a.strip() for a in sys.argv[1:] if a.strip()}
    today = datetime.date.today()

    print(f"Date: {today}  | Absent Sn. numbers: {sorted(absent) or 'none'}")

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            PROFILE_DIR, headless=False,channel="chrome", 
args=["--start-maximized"], no_viewport=True
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(LOGIN_URL)

        login_id = os.environ.get("SAMAGAM_ID")
        password = os.environ.get("SAMAGAM_PASS")
        if login_id and password:
            page.get_by_placeholder("Enter Your Login ID").fill(login_id)
            page.get_by_placeholder("Enter Your Password").fill(password)
            try:
                page.frame_locator("iframe[src*='challenges.cloudflare.com']").get_by_text(
                    "Success!"
                ).wait_for(timeout=30000)
            except Exception:
                input("Cloudflare not confirmed. Complete it manually, then press Enter... ")
            page.get_by_role("button", name="Login").click()
            page.wait_for_load_state("networkidle")
        else:
            input("Log in (and pass any check) in the browser, then press Enter here... ")

        if ATTENDANCE_URL:
            page.goto(ATTENDANCE_URL)
        for text in NAV_STEPS:
            page.get_by_text(text, exact=(text != "View / Edit")).first.click()
            page.wait_for_load_state("networkidle")

        for label, value in FILTERS.items():
            page.get_by_label(label).select_option(label=value)
            page.wait_for_load_state("networkidle")

        page.wait_for_selector(ROW_SELECTOR)
        page.once("dialog", lambda d: d.accept())  # accept any confirm popup after Save

        rows = page.locator(ROW_SELECTOR)
        count = rows.count()
        if count == 0:
            sys.exit("No student rows found. Check ROW_SELECTOR.")

        found = set()
        for i in range(count):
            row = rows.nth(i)
            sn = row.locator(ROLL_SELECTOR).first.inner_text().strip()
            if sn in absent:
                set_status(row, ABSENT_LABEL)
                found.add(sn)
            # everyone else is left untouched (portal default is Present)

        missing = absent - found
        if missing:
            sys.exit(f"Sn. numbers not found: {sorted(missing)}. NOT saved.")

        print(f"Students: {count} | Absent: {len(found)} | Present: {count - len(found)}")
        shot = f"attendance_{today.isoformat()}.png"
        page.screenshot(path=shot, full_page=True)

        page.get_by_role("button", name=SUBMIT_TEXT).first.click()
        page.wait_for_load_state("networkidle")
        page.screenshot(path=f"attendance_{today.isoformat()}_after_submit.png", full_page=True)
        print("Saved. Screenshots saved. Check them to confirm.")
        page.wait_for_timeout(3000)
        ctx.close()


if __name__ == "__main__":
    main()
