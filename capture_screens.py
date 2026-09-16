import time
from playwright.sync_api import sync_playwright
from core.ledger_analyzer import generate_sample_ledger_csv

# Prepare sample CSV
with open('test_sample_ledger.csv', 'w', encoding='utf-8') as f:
    f.write(generate_sample_ledger_csv())

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={'width': 1280, 'height': 820})

    # 1. GSTIN Verifier Tab
    page.goto('http://127.0.0.1:8000', wait_until='networkidle')
    time.sleep(1)
    page.click('#nav-gstin')
    time.sleep(0.5)
    page.click('#btn-verify-gstin')
    time.sleep(1.5)
    page.screenshot(path='screenshot_gstin.png')
    print("Captured: screenshot_gstin.png")

    # 2. Section 43B(h) Ledger Scanner Tab
    page.click('#nav-ledger')
    time.sleep(0.5)
    page.set_input_files('#ledger-file-input', 'test_sample_ledger.csv')
    time.sleep(1.5)
    page.screenshot(path='screenshot_ledger.png')
    print("Captured: screenshot_ledger.png")

    # 3. CA Portfolio Tab
    page.click('#nav-ca')
    time.sleep(1.5)
    page.screenshot(path='screenshot_ca.png')
    print("Captured: screenshot_ca.png")

    browser.close()
