"""Mark attendance on the KVS Samagam portal. Login is done manually by you in Brave.

Usage: python mark.py 27 29 32
(27 29 32 = Sn. numbers of ABSENT students; none = all present)
"""
import re
import sys
import time
import subprocess
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

BRAVE = "/usr/bin/brave-browser"
PROFILE_DIR = Path.home() / ".attendance-brave"  # keeps your login between runs
DEBUG_PORT = 9222
HOME_URL = "https://samagam.kvs.gov.in"

host = urlparse(HOME_URL).netloc
absent = set(sys.argv[1:])

subprocess.Popen(
    [BRAVE, f"--remote-debugging-port={DEBUG_PORT}", f"--user-data-dir={PROFILE_DIR}", HOME_URL],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
time.sleep(3)

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(f"http://localhost:{DEBUG_PORT}")
    pages = [pg for c in browser.contexts for pg in c.pages if host in pg.url]
    if not pages:
        sys.exit("Portal tab not found in the Brave window.")
    page = pages[0]
    page.bring_to_front()
    page.wait_for_load_state("domcontentloaded")

    input("Log in manually in Brave (skip if already logged in), then press Enter here... ")
    page.wait_for_load_state("domcontentloaded")
    time.sleep(2)
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
