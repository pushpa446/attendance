"""
Usage: python mark.py --id LOGIN_ID --password 'PASSWORD' 27 29 32
(27 29 32 = Sn. numbers of ABSENT students; none = all present)

Opens a normal, visible Brave window, fills your ID and password, waits for you to
pass the Cloudflare check and press Enter, then marks the attendance.
"""
import sys
import re
import time
import shutil
import argparse
import subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser()
parser.add_argument("--id")
parser.add_argument("--password")
parser.add_argument("absent", nargs="*")
args = parser.parse_args()
absent = set(args.absent)

brave = next(
    (
        b
        for b in (
            shutil.which("brave-browser"),
            shutil.which("brave-browser-stable"),
            shutil.which("brave"),
            "/snap/bin/brave",
            "/opt/brave.com/brave/brave-browser",
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
            str(Path.home() / "Applications/Brave Browser.app/Contents/MacOS/Brave Browser"),
        )
        if b and Path(b).exists()
    ),
    None,
)
if not brave:
    sys.exit("Brave not found. Run: which brave brave-browser   and edit the path in mark.py")

subprocess.Popen(
    [
        brave,
        "--remote-debugging-port=9222",
        f"--user-data-dir={Path.home() / '.attendance-chrome'}",
        "https://samagam.kvs.gov.in/?login=1",
    ],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
time.sleep(3)

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    pages = [pg for c in browser.contexts for pg in c.pages if "samagam.kvs.gov.in" in pg.url]
    if not pages:
        sys.exit("No Samagam tab found in the Brave window.")
    page = pages[0]
    page.bring_to_front()

    # Login (skipped if the saved Brave profile is already logged in)
    page.wait_for_load_state("domcontentloaded")
    time.sleep(3)  # let redirects finish
    login_box = page.get_by_placeholder("Enter Your Login ID")
    print("Page:", page.url)
    logged_in = any(k in page.url for k in ("/dashboard", "/dashboar", "/mis/")) or not (
        login_box.count() and login_box.first.is_visible()
    )
    if logged_in:
        print("Already logged in.")
    else:
        print("Not logged in, filling login form...")
        if not (args.id and args.password):
            sys.exit("Not logged in. Run again with --id and --password.")
        login_box.first.fill(args.id)
        page.get_by_placeholder("Enter Your Password").fill(args.password)
        input("Wait for Cloudflare 'Success!', then press Enter to login... ")
        page.get_by_role("button", name="Login").click()
        page.wait_for_load_state("domcontentloaded")
        time.sleep(3)
    print("Opening attendance page...")

    # Go to attendance
    for text in ["SIS", "Attendance", "Mark Attendance"]:
        page.get_by_text(text, exact=True).first.click()
        page.wait_for_load_state("networkidle")
    page.get_by_text(re.compile(r"^\s*(Mark|View / Edit)\s*$")).first.click()  # first time: Mark, later: View / Edit
    page.wait_for_selector("table tbody tr")

    # Set absentees (everyone else stays Present)
    found = set()
    rows = page.locator("table tbody tr")
    total = rows.count()
    for i in range(total):
        row = rows.nth(i)
        sn = row.locator("td").first.inner_text().strip()
        if sn in absent:
            row.locator("select").first.select_option(label="Absent")
            found.add(sn)

    if absent - found:
        sys.exit(f"Sn. not found: {sorted(absent - found)}. Not saved.")

    page.screenshot(path="attendance.png", full_page=True)
    page.get_by_role("button", name="Save", exact=True).first.click()

    # Verify the summary popup against what you asked for, then confirm
    popup = page.get_by_text("Confirm Attendance Summary").locator(
        "xpath=ancestor::*[.//button[contains(., 'Confirm')]][1]"
    )
    popup.wait_for()
    text = popup.inner_text()
    shown_absent = int(re.search(r"Absent\s+(\d+)", text).group(1))
    shown_present = int(re.search(r"Present\s+(\d+)", text).group(1))
    want_absent, want_present = len(found), total - len(found)
    if (shown_absent, shown_present) != (want_absent, want_present):
        sys.exit(
            f"Popup shows Absent {shown_absent}, Present {shown_present} but expected "
            f"Absent {want_absent}, Present {want_present}. NOT confirmed."
        )
    page.get_by_role("button", name="Confirm & Save").click()
    page.wait_for_load_state("networkidle")
    print(f"Saved. Absent: {sorted(found) or 'none'}")