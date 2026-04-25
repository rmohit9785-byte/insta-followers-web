from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://www.instagram.com/")
    print("Log in manually, then press Enter here...")
    input()
    context.storage_state(path="ig_state.json")
    browser.close()
