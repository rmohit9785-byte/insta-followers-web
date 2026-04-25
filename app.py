cat > app.py << 'EOF'
import re
from datetime import datetime

import gspread
import streamlit as st
from google.oauth2.service_account import Credentials
from playwright.sync_api import sync_playwright

SERVICE_FILE = "service_account.json"
STATE_FILE = "ig_state.json"
DATE_FORMAT = "%Y-%m-%d " + "%H:%M:%S"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def parse_count(text):
    text = str(text).lower()
    text = text.replace(",", "").strip()
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


def get_sheet(sheet_url, worksheet_name):
    creds = Credentials.from_service_account_file(
        SERVICE_FILE,
        scopes=SCOPES
    )
    gc = gspread.authorize(creds)
    sh = gc.open_by_url(sheet_url)
    return sh.worksheet(worksheet_name)


def fetch_followers(page, profile_url):
    page.goto(
        profile_url,
        wait_until="domcontentloaded",
        timeout=60000
    )
    page.wait_for_timeout(3000)

    selectors = [
        'a[href$="/followers/"] span[title]',
        'header section ul li:nth-child(2) span[title]',
        'header section ul li:nth-child(2) a span[title]',
        'header section ul li:nth-child(2) span',
    ]

    for selector in selectors:
        try:
            loc = page.locator(selector).first
            if loc.count() > 0:
                title = loc.get_attribute("title")
                text = title or loc.inner_text()
                value = parse_count(text)
                if value is not None:
                    return value
        except Exception:
            pass

    try:
        body = page.locator("body").inner_text().lower()
        match = re.search(
            r"([\d.,]+[kmb]?)\s+followers",
            body
        )
        if match:
            return parse_count(match.group(1))
    except Exception:
        pass

    return None


def update_followers(sheet_url, worksheet_name):
    ws = get_sheet(sheet_url, worksheet_name)
    rows = ws.get_all_values()
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state=STATE_FILE)
        page = context.new_page()

        total = len(rows) - 1

        for i, row in enumerate(rows[1:], start=2):
            name = row[0] if len(row) > 0 else ""
            link = row[1] if len(row) > 1 else ""

            if not link:
                ws.update(f"E{i}", [["No link"]])
                results.append((name, "No link"))
                continue

            try:
                followers = fetch_followers(page, link)

                if followers is None:
                    ws.update(f"E{i}", [["Could not read"]])
                    results.append((name, "Could not read"))
                    continue

                now = datetime.now().strftime(DATE_FORMAT)

                ws.update(f"C{i}", [[followers]])
                ws.update(f"D{i}", [[now]])
                ws.update(f"E{i}", [["Done"]])

                results.append((name, followers))
                page.wait_for_timeout(2500)

            except Exception as e:
                err = str(e)[:60]
                ws.update(f"E{i}", [[f"Error: {err}"]])
                results.append((name, f"Error: {err}"))

        browser.close()

    return results


st.set_page_config(
    page_title="Instagram Followers Updater",
    page_icon="📊"
)

st.title("Instagram Followers Updater")

st.write("Paste a Google Sheet URL.")
st.write("The sheet must have this format:")

st.code(
    "Name | Profile Link | Followers | Last Updated | Status"
)

sheet_url = st.text_input("Google Sheet URL")
worksheet_name = st.text_input("Worksheet name", value="Sheet1")

st.warning(
    "The sheet must be shared as Editor "
    "with your service account email."
)

if st.button("Update Followers"):
    if not sheet_url:
        st.error("Please paste a Google Sheet URL.")
    else:
        with st.spinner("Updating followers..."):
            try:
                results = update_followers(
                    sheet_url,
                    worksheet_name
                )
                st.success("Followers updated successfully.")

                for name, result in results:
                    st.write(f"{name} → {result}")

            except Exception as e:
                st.error(f"Error: {e}")
