"""
run_experiment.py — menjalankan matriks pengujian S1-S4 secara otomatis.

Protokol (proposal 9.3):
  - 2 warm-up run per kombinasi (hasil dibuang)
  - 5 measurement run
  - jeda 30 detik antar run
  - urutan kombinasi diacak per sesi
  - CV > 20% -> ditandai untuk diulang
"""
import csv
import os
import random
import re
import statistics
import time
from datetime import datetime

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()
URL = os.environ["POWERAPPS_URL"]

WARMUP_RUNS = 2
MEASURE_RUNS = 5
DELAY_SECONDS = 30
STATUS_TIMEOUT_MS = 900_000   # 5 menit; S3 di 10k bisa lama
CV_THRESHOLD = 0.20

EXT_SCALES_FULL = ["5k", "10k", "50k", "100k"]
EXT_SCALES_LIMITED = ["5k", "10k"]
DATASETS = ["UCI", "OLIST"]
SOURCES = ["SQL", "DV"]

# Kombinasi sesuai batasan desain: S1 & S4 lima skala, S2 & S3 dua skala
EXT_SCALES = [f"{d}{sc}" for d in ("UCI", "OLIST") for sc in ("5k", "10k", "50k", "100k")]
COMBOS = (
    [(p, s, sc) for p in ("S1", "S4") for s in ("DV", "SQL") for sc in EXT_SCALES]          # 32
    + [("S2", s, f"{d}{sc}") for s in ("DV", "SQL") for d in ("UCI", "OLIST") for sc in ("5k", "10k")]  # 8
)
assert len(COMBOS) == 40

# --- SESUAIKAN setelah discover_selectors.py ---
SEL_PARAM = '[data-control-name="txtParam"] input'
SEL_STATUS = '[data-control-name="lblStatus"]'
SEL_BUTTON = '[data-control-name="btn{pattern}"]'
FRAME_URL_PART = "runtime-app.powerplatform.com/publishedapp"
# -----------------------------------------------

OUT_DIR = "results"
os.makedirs(OUT_DIR, exist_ok=True)
OUT_PATH = os.path.join(
    OUT_DIR, f"ext_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
)
FIELDS = [
    "timestamp", "pattern", "source", "scale", "run_no", "phase",
    "rows", "roundtrip_ms", "fn_ms", "raw_status",
]


def get_frame(page):
    for f in page.frames:
        if FRAME_URL_PART in f.url:
            return f
    raise RuntimeError("Frame app tidak ditemukan — cek apakah app sudah dimuat penuh")


def parse_status(raw):
    """DONE|S1|SQL_5k|984|412  atau  DONE|S4|SQL_5k|984|1140|fnms=45.95"""
    parts = raw.split("|")
    if len(parts) < 5 or parts[0] != "DONE":
        return None
    out = {"rows": int(parts[3]), "roundtrip_ms": int(parts[4]), "fn_ms": ""}
    for extra in parts[5:]:
        m = re.match(r"fnms=([\d.]+)", extra)
        if m:
            out["fn_ms"] = float(m.group(1))
    return out


def single_run(page, pattern, source, scale):
    frame = get_frame(page)
    param = f"{source}_{scale}"
    expected = f"DONE|{pattern}|{param}|"

    frame.fill(SEL_PARAM, "")
    frame.fill(SEL_PARAM, param)
    page.wait_for_timeout(500)

    frame.click(SEL_BUTTON.format(pattern=pattern))

    # tunggu Power Apps memulai eksekusi, supaya status lama tidak terbaca
    t_run = time.time() + 10
    while time.time() < t_run:
        if (frame.text_content(SEL_STATUS) or "").strip() == "RUNNING":
            break
        page.wait_for_timeout(50)

    deadline = time.time() + STATUS_TIMEOUT_MS / 1000
    while time.time() < deadline:
        raw = (frame.text_content(SEL_STATUS) or "").strip()
        if raw.startswith(expected) or raw.startswith("ERR"):
            return raw
        page.wait_for_timeout(500)

    return "ERR|TIMEOUT"


def main():
    session_combos = COMBOS[:]
    random.shuffle(session_combos)

    rows_out = []
    summary = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        ctx = browser.new_context(storage_state="auth_state.json")
        page = ctx.new_page()
        page.goto(URL)
        print("Memuat app, tunggu 40 detik...")
        page.wait_for_timeout(40000)

        for idx, (pattern, source, scale) in enumerate(session_combos, 1):
            label = f"{pattern} {source}_{scale}"
            print(f"\n[{idx}/{len(session_combos)}] {label}")

            for w in range(1, WARMUP_RUNS + 1):
                raw = single_run(page, pattern, source, scale)
                print(f"   warmup {w}: {raw}")
                rows_out.append({
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                    "pattern": pattern, "source": source, "scale": scale,
                    "run_no": w, "phase": "warmup",
                    "rows": "", "roundtrip_ms": "", "fn_ms": "",
                    "raw_status": raw,
                })
                time.sleep(DELAY_SECONDS)

            durations = []
            for r in range(1, MEASURE_RUNS + 1):
                raw = single_run(page, pattern, source, scale)
                parsed = parse_status(raw)
                print(f"   run {r}: {raw}")
                rec = {
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                    "pattern": pattern, "source": source, "scale": scale,
                    "run_no": r, "phase": "measure",
                    "rows": "", "roundtrip_ms": "", "fn_ms": "",
                    "raw_status": raw,
                }
                if parsed:
                    rec.update(parsed)
                    durations.append(parsed["roundtrip_ms"])
                rows_out.append(rec)

                with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=FIELDS)
                    writer.writeheader()
                    writer.writerows(rows_out)

                if r < MEASURE_RUNS:
                    time.sleep(DELAY_SECONDS)

            if len(durations) >= 2:
                mean = statistics.mean(durations)
                cv = statistics.stdev(durations) / mean if mean else 0
                flag = "PERLU DIULANG" if cv > CV_THRESHOLD else "ok"
                print(f"   mean={mean:.0f} ms  CV={cv:.1%}  {flag}")
                summary.append((label, mean, cv, flag))
            else:
                print("   GAGAL: data measurement tidak cukup")
                summary.append((label, 0, 0, "GAGAL"))

            time.sleep(DELAY_SECONDS)

        browser.close()

    print("\n" + "=" * 60)
    print("RINGKASAN SESI")
    for label, mean, cv, flag in summary:
        print(f"  {label:<16} mean={mean:>9.0f} ms  CV={cv:>6.1%}  {flag}")
    print(f"\nHasil mentah: {OUT_PATH}")


if __name__ == "__main__":
    main()