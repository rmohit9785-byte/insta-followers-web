import os
import re
from datetime import datetime

import gspread
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from playwright.sync_api import sync_playwright

load_dotenv()

SERVICE_FILE = "service_account.json"
STATE_FILE = "ig_state.json"
SHEET_URL = os.getenv("GOOGLE_SHEET_URL")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def parse_count(text):
    text = text.lower().replace(",", "").strip()
    match = re.search(r"([\d.]+)\s*([kmb]?)", text)
    if not match:
        return None

    num = float(match.group(1))
    suffix = match.group(2)

    if suffix == "k":
        num *= 1000
    elif suffix == "m":
        num *= 1000000
    elif suffix == "b":
        num *= 1000000000

    return int(num)


def main():
    creds = Credentials.from_service_account_file(SERVICE_FILE, 
scopes=SCOPES)
    gc = gspread.authorize(creds)
    sheet = gc.open_by_url(SHEET_URL).sheet1

    rows = sheet.get_all_values()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state=STATE_FILE)
        page = context.new_page()

        for i, row in enumerate(rows[1:], start=2):
            name = row[0]
            link = row[1]

            if not link:
                continue

            try:
                page.goto(link)
                page.wait_for_timeout(4000)

                text = page.locator("body").inner_text().lower()
                match = re.search(r"([\d.,]+[kmb]?) followers", text)

                if match:
                    followers = parse_count(match.group(1))

                    sheet.update(f"C{i}", [[followers]])
                    sheet.update(f"D{i}", 
[[datetime.now().strftime("%Y-%m-%d %H:%M:%S")]])
                    sheet.update(f"E{i}", [["Done"]])

                    print(f"{name} -> {followers}")
                else:
                    sheet.update(f"E{i}", [["Not found"]])

                page.wait_for_timeout(3000)

            except Exception as e:
                sheet.update(f"E{i}", [[str(e)]])
                print("Error:", e)

        browser.close()


if __name__ == "__main__":
    main()
