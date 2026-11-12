"""
auth_setup.py — login manual sekali, simpan sesi ke auth_state.json.
Jalankan ulang kalau sesi kedaluwarsa (biasanya beberapa minggu).
"""
import os
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()
URL = os.environ["POWERAPPS_URL"]


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        ctx = browser.new_context()
        page = ctx.new_page()
        page.goto(URL)

        print("=" * 60)
        print("Login manual di jendela browser yang terbuka.")
        print("Tunggu sampai app-nya benar-benar tampil dan tombol S1-S4 kelihatan.")
        print("Kalau sudah, kembali ke sini dan tekan ENTER.")
        print("=" * 60)
        input()

        ctx.storage_state(path="auth_state.json")
        print("Sesi tersimpan ke auth_state.json")
        browser.close()


if __name__ == "__main__":
    main()