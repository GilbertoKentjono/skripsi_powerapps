"""
discover_selectors.py — dump semua data-control-name yang ada di halaman.
Tujuan: memastikan Playwright bisa "melihat" txtParam, btnS1..btnS4, lblStatus.
"""
import os
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()
URL = os.environ["POWERAPPS_URL"]


def dump(frame, label):
    names = frame.eval_on_selector_all(
        "[data-control-name]",
        "els => els.map(e => e.getAttribute('data-control-name'))",
    )
    if names:
        print(f"\n--- {label} ---")
        for n in sorted(set(names)):
            print("  ", n)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        ctx = browser.new_context(storage_state="auth_state.json")
        page = ctx.new_page()
        page.goto(URL)

        print("Menunggu app selesai dimuat (30 detik)...")
        page.wait_for_timeout(30000)

        dump(page.main_frame, "MAIN FRAME")
        for i, f in enumerate(page.frames):
            if f is not page.main_frame:
                try:
                    dump(f, f"IFRAME {i}: {f.url[:70]}")
                except Exception:
                    pass

        print("\nTekan ENTER untuk menutup.")
        input()
        browser.close()


if __name__ == "__main__":
    main()