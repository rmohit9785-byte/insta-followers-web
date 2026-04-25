import re
import time
from datetime import datetime

import gspread
import streamlit as st
from google.oauth2.service_account import Credentials
from playwright.sync_api import sync_playwright

# 🔐 CONFIG
BOT_EMAIL = "insta-followers-updater@insta-followers-updater-493919.iam.gserviceaccount.com"
SERVICE_FILE = "service_account.json"
STATE_FILE = "ig_state.json"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

ACCESS_CODE = "Rawatji09876"
APP_ACTIVE = True

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


# 🚫 ADMIN CONTROL
if not APP_ACTIVE:
    st.error("🚫 Service is paused by admin")
    st.stop()

# 🔐 AUTH SYSTEM
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔐 Private Access")

    code_input = st.text_input("Enter Access Code", type="password")

    if st.button("Login"):
        if code_input == ACCESS_CODE:
            st.session_state.authenticated = True
            st.success("Access granted ✅")
            st.rerun()
        else:
            st.error("Wrong code ❌")

    st.stop()

# 🔢 HELPERS
def parse_count(text):
    text = str(text).lower().replace(",", "").strip()
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
    page.goto(profile_url, wait_until="domcontentloaded", timeout=60000)
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

    return None

# 🚀 MAIN FUNCTION
def update_followers(sheet_url, worksheet_name):
    ws = get_sheet(sheet_url, worksheet_name)
    rows = ws.get_all_values()

    total = max(len(rows) - 1, 0)

    progress_bar = st.progress(0)
    status_text = st.empty()
    results_box = st.container()

    start_time = time.time()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        context = browser.new_context(storage_state=STATE_FILE)
        page = context.new_page()

        for idx, row in enumerate(rows[1:], start=1):
            sheet_row = idx + 1

            name = row[0] if len(row) > 0 else ""
            link = row[1] if len(row) > 1 else ""

            status_text.info(f"Processing {idx} / {total} → {name}")

            if total > 0:
                progress_bar.progress(idx / total)

            if not link:
                ws.update(f"E{sheet_row}", [["No link"]])
                results_box.write(f"{idx}/{total} → No link")
                continue

            try:
                followers = fetch_followers(page, link)

                if followers is None:
                    ws.update(f"E{sheet_row}", [["Could not read"]])
                    results_box.write(f"{idx}/{total} → Could not read")
                    continue

                now = datetime.now().strftime(DATE_FORMAT)

                ws.update(f"C{sheet_row}", [[followers]])
                ws.update(f"D{sheet_row}", [[now]])
                ws.update(f"E{sheet_row}", [["Done"]])

                results_box.write(f"{idx}/{total} → {followers}")
                page.wait_for_timeout(2000)

            except Exception as e:
                err = str(e)[:60]
                ws.update(f"E{sheet_row}", [[f"Error: {err}"]])
                results_box.write(f"{idx}/{total} → Error")

        browser.close()

    elapsed = int(time.time() - start_time)
    minutes = elapsed // 60
    seconds = elapsed % 60

    status_text.success(f"✅ Completed in {minutes} min {seconds} sec")

# 🎨 UI
st.set_page_config(page_title="Instagram Followers Updater", 
page_icon="📊")

st.title("🚀 Instagram Followers Updater")
st.caption("A prototype by Mohit Rawat")

st.write("Update Instagram followers directly in your Google Sheet")

st.subheader("📋 Required Format")
st.code("Name | Profile Link | Followers | Last Updated | Status")

st.subheader("🔑 Step 1: Share your sheet with bot email")
st.code(BOT_EMAIL)

st.subheader("📎 Step 2: Paste your sheet URL")

sheet_url = st.text_input("Google Sheet URL")
worksheet_name = st.text_input("Worksheet Name", value="Sheet1")

# ▶️ BUTTON
if st.button("🚀 Update Followers"):
    if not sheet_url:
        st.error("Paste sheet URL")
    else:
        st.success("Starting process...")
        update_followers(sheet_url, worksheet_name)
