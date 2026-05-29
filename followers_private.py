import os
import re
import json
import time
from datetime import datetime
import gspread
import streamlit as st
from google.oauth2.service_account import Credentials
from playwright.sync_api import sync_playwright
import random
st.set_page_config(
    page_title="GrowthSheet",
    page_icon="🚀",
    layout="wide"
)
BOT_EMAIL = "update-followers@insta-followers-updater-493919.iam.gserviceaccount.com"
STATE_FILE = "ig_state.json"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
ACCESS_CODE = "Rawatji09876"
APP_ACTIVE = True
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
st.markdown("""
<style>
.stApp {
    background: radial-gradient(circle at top left, #1c1035 0%, #090b13 
45%, #05060a 100%);
    color: white;
}
[data-testid="stHeader"] {
    background: transparent;
}
.block-container {
    padding-top: 2rem;
    max-width: 1200px;
}
    background: linear-gradient(135deg, rgba(30,32,55,0.95), 
rgba(9,11,20,0.95));
    border: 1px solid rgba(139,92,246,0.35);
    border-radius: 24px;
    padding: 32px;
    box-shadow: 0 0 40px rgba(124,58,237,0.18);
}
.glass-card {
    background: rgba(18, 21, 36, 0.82);
    border: 1px solid rgba(139,92,246,0.35);
    border-radius: 20px;
    padding: 24px;
    box-shadow: 0 0 25px rgba(0,0,0,0.25);
}
.step-badge {
    background: linear-gradient(135deg, #2563eb, #9333ea);
    padding: 10px 16px;
    border-radius: 12px;
    font-weight: 800;
    margin-right: 12px;
}
.info-box {
    background: rgba(88,28,135,0.22);
    border: 1px solid rgba(168,85,247,0.55);
    color: #d8b4fe;
    padding: 14px;
    border-radius: 14px;
}
.success-box {
    background: rgba(6,78,59,0.55);
    border: 1px solid rgba(16,185,129,0.65);
    padding: 18px;
    border-radius: 16px;
}
.metric-card {
    background: rgba(15,23,42,0.85);
    border: 1px solid rgba(59,130,246,0.35);
    border-radius: 18px;
    padding: 20px;
    text-align: center;
}
.big-title {
    font-size: 44px;
    font-weight: 900;
    margin-bottom: 0px;
}
.gradient-text {
    background: linear-gradient(90deg, #22c55e, #3b82f6, #a855f7);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.stButton > button {
    background: linear-gradient(90deg, #2563eb, #9333ea);
    color: white;
    border: none;
    border-radius: 14px;
    padding: 12px 28px;
    font-weight: 800;
    box-shadow: 0 0 20px rgba(147,51,234,0.35);
}
.stTextInput input {
    background: rgba(15,23,42,0.9);
    border-radius: 12px;
    border: 1px solid rgba(148,163,184,0.25);
    color: white;
}
</style>
""", unsafe_allow_html=True)
if not APP_ACTIVE:
    st.error("🚫 Service is paused by admin.")
    st.stop()
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if not st.session_state.authenticated:
    st.markdown("<h1 class='big-title'>🔐 GrowthSheet Access</h1>", 
unsafe_allow_html=True)
    st.caption("A prototype by Mohit Rawat | Version 2")
    st.write("Enter your private access code to continue.")
    code_input = st.text_input("Access Code", type="password")
    if st.button("Login"):
        if code_input == ACCESS_CODE:
            st.session_state.authenticated = True
            st.success("Access granted ✅")
            st.rerun()
        else:
            st.error("Wrong access code ❌")
    st.stop()

def format_like_instagram(number):
    if number is None:
        return ""

    try:
        number = int(number)
    except Exception:
        return number

    # Under 10K keep exact number
    if number < 10_000:
        return number

    # 10K to 99.9K -> keep 1 decimal K expanded
    # 27,765 -> 27,700
    if number < 100_000:
        return (number // 100) * 100

    # 100K to 999K -> whole K expanded
    # 232,674 -> 232,000
    if number < 1_000_000:
        return (number // 1_000) * 1_000

    # Millions -> one decimal M expanded
    # 7,465,256 -> 7,400,000
    return (number // 100_000) * 100_000


def parse_count(text):
    if text is None:
        return None

    text = str(text).strip().replace(",", "")
    text = text.replace("\n", " ")

    match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*([KkMmBb]?)", text)

    if not match:
        return None

    num = float(match.group(1))
    suffix = match.group(2).lower()

    if suffix == "k":
        num *= 1000
    elif suffix == "m":
        num *= 1000000
    elif suffix == "b":
        num *= 1000000000

    return int(num)


def get_sheet(sheet_url, worksheet_name):
    service_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not service_json:
        raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON is missing in Railway variables")
    service_info = json.loads(service_json)
    creds = Credentials.from_service_account_info(
        service_info,
        scopes=SCOPES
    )
    gc = gspread.authorize(creds)
    sh = gc.open_by_url(sheet_url)
    return sh.worksheet(worksheet_name)
def normalize_instagram_url(url):
    url = str(url).strip()

    if not url:
        return None

    # If only username is given, convert it to full Instagram URL
    if "instagram.com" not in url:
        username = url.strip().strip("@").strip("/")
        if not username:
            return None
        return "https://www.instagram.com/" + username + "/"

    # Fix common broken URL formats
    url = url.replace("https:/www.", "https://www.")
    url = url.replace("https:/instagram.com", "https://www.instagram.com")
    url = url.replace("http:/www.", "https://www.")
    url = url.replace("http:/instagram.com", "https://www.instagram.com")

    if url.startswith("www.instagram.com"):
        url = "https://" + url

    if url.startswith("instagram.com"):
        url = "https://www." + url

    if not url.startswith("http"):
        return None

    if not url.endswith("/"):
        url = url + "/"

    return url


def fetch_followers(page, profile_url):
    try:
        profile_url = normalize_instagram_url(profile_url)

        if not profile_url:
            return None

        page.goto(
            profile_url,
            wait_until="domcontentloaded",
            timeout=18000
        )

        page.wait_for_timeout(random.randint(900, 1400))

        # Method 1: visible body text. This matches your debug output:
        # "8.5M followers"
        try:
            body = page.locator("body").inner_text(timeout=3000)
            body_clean = body.replace("\n", " ")

            match = re.search(
                r"([0-9]+(?:\.[0-9]+)?\s*[KkMmBb]?|[0-9,]+)\s+followers",
                body_clean,
                re.IGNORECASE
            )

            if match:
                value = parse_count(match.group(1))
                if value is not None:
                    return value
        except Exception:
            pass

        # Method 2: meta description
        try:
            meta = page.locator('meta[property="og:description"]').first

            if meta.count() > 0:
                content = meta.get_attribute("content")

                if content:
                    match = re.search(
                        r"([0-9]+(?:\.[0-9]+)?\s*[KkMmBb]?|[0-9,]+)\s+Followers",
                        content,
                        re.IGNORECASE
                    )

                    if match:
                        value = parse_count(match.group(1))
                        if value is not None:
                            return value
        except Exception:
            pass

        # Method 3: profile selectors
        selectors = [
            'a[href$="/followers/"] span[title]',
            'a[href$="/followers/"] span',
            'header section ul li:nth-child(2) span[title]',
            'header section ul li:nth-child(2) span',
            'span[title]'
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

    except Exception as e:
        raise Exception("Profile load timeout or crash: " + str(e).replace("\n", " ")[:100])


def update_followers(sheet_url, worksheet_name):
    ws = get_sheet(sheet_url, worksheet_name)
    rows = ws.get_all_values()
    total = max(len(rows) - 1, 0)
    progress_bar = st.progress(0)
    status_text = st.empty()
    result_box = st.container()
    start_time = time.time()
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
        )
        context = browser.new_context(storage_state=STATE_FILE)
        page = context.new_page()
        page.set_default_timeout(15000)
        page.set_default_navigation_timeout(15000)

        def block_heavy_resources(route):
            if route.request.resource_type in ["image", "media", "font"]:
                route.abort()
            else:
                route.continue_()

        page.route("**/*", block_heavy_resources)
        for idx, row in enumerate(rows[1:], start=1):
            try:
                page.title()
            except Exception:
                try:
                    browser.close()
                except Exception:
                    pass

                browser = p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
                )
                context = browser.new_context(storage_state=STATE_FILE)
                page = context.new_page()
                page.set_default_timeout(15000)
                page.set_default_navigation_timeout(15000)

            if idx > 1 and idx % 75 == 1:
                try:
                    browser.close()
                except Exception:
                    pass

                browser = p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
                )
                context = browser.new_context(storage_state=STATE_FILE)
                page = context.new_page()
                page.set_default_timeout(15000)
                page.set_default_navigation_timeout(15000)

            sheet_row = idx + 1
            name = row[0] if len(row) > 0 else ""
            link = row[1] if len(row) > 1 else ""
            status_text.info(f"Processing {idx} / {total} → {name}")
            if total > 0:
                progress_bar.progress(idx / total)
            if not link:
                ws.update(f"E{sheet_row}", [["No link"]])
                time.sleep(0.3)
                result_box.write(str(idx) + "/" + str(total) + " → " + str(name) + " → No link")
                continue
            try:
                followers = fetch_followers(page, link)
                if followers is None:
                    ws.update(f"E{sheet_row}", [["Could not read"]])
                    time.sleep(0.3)
                    result_box.write(str(idx) + "/" + str(total) + " → " + str(name) + " → Could not read")
                    continue
                formatted_followers = format_like_instagram(followers)

                now = datetime.now().strftime(DATE_FORMAT)
                ws.update(
                    f"C{sheet_row}:E{sheet_row}",
                    [[formatted_followers, now, "Done"]]
                )
                time.sleep(0.3)
                result_box.write(str(idx) + "/" + str(total) + " → " + str(name) + " → " + str(followers))
                page.wait_for_timeout(random.randint(900, 1400))
            except Exception as e:
                err = str(e).replace("\n", " ")[:80]
                ws.update(f"E{sheet_row}", [[f"Error: {err}"]])
                time.sleep(0.3)
                result_box.write(str(idx) + "/" + str(total) + " → " + str(name) + " → Error: " + str(err))
        browser.close()
    elapsed = int(time.time() - start_time)
    minutes = elapsed // 60
    seconds = elapsed % 60
    return total, minutes, seconds
st.markdown("""
    <div style="display:flex; justify-content:space-between; 
align-items:center;">
        <div>
            <h1 class="big-title">🚀 GrowthSheet</h1>
            <p style="color:#a1a1aa;">A prototype by Mohit Rawat | Version 
2</p>
            <h3 class="gradient-text">Automate. Track. Grow.</h3>
            <p>Update Instagram followers directly in your Google 
Sheet.</p>
        </div>
        <div style="font-size:70px;">📊</div>
    </div>
</div>
""", unsafe_allow_html=True)
st.write("")
main_col, status_col = st.columns([2, 1])
with main_col:
    st.markdown("## 1️⃣ Share your sheet with bot email")
    st.write("Share your Google Sheet with this email as **Editor**:")
    st.code(BOT_EMAIL)
    st.info("Required format: Name | Profile Link | Followers | Last Updated | Status")
    st.markdown("## 2️⃣ Paste your Google Sheet URL")
    sheet_url = st.text_input(
        "Google Sheet URL",
        placeholder="https://docs.google.com/spreadsheets/d/..."
    )
    worksheet_name = st.text_input("Worksheet Name", value="Sheet1")
    start_clicked = st.button("🚀 Update Followers")
with status_col:
    st.markdown("## ✨ Live Status")
    st.success("✅ System online")
    st.metric("Current Status", "Ready")
    st.metric("Sheet Format", "5 columns")
    st.metric("Access", "Private beta")
if start_clicked:
    if not sheet_url:
        st.error("Please paste your Google Sheet URL.")
    else:
        st.subheader("⚡ Updating now...")
        top_result_box = st.empty()
        try:
            top_result_box.info("⏱️ Running... time will appear here")

            result = update_followers(sheet_url, worksheet_name)

            if len(result) == 4:
                total, minutes, seconds, avg_seconds = result
            else:
                total, minutes, seconds = result
                elapsed_total = (minutes * 60) + seconds
                avg_seconds = elapsed_total / total if total else 0

            top_result_box.success(
                f"✅ Completed {total} rows in {minutes} min {seconds} sec ({avg_seconds:.2f}s/profile)"
            )
        except Exception as e:
            st.error(f"Error: {e}")
st.caption("Made with ❤️ by Mohit Rawat | GrowthSheet")
