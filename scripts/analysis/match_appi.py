"""Pasangkan request App Insights (UTC) dengan run S4 di CSV eksperimen (WIB)."""
import pandas as pd, numpy as np
a = pd.read_csv("appi.csv", encoding="utf-8-sig")
a.columns = ["ts","duration","success","code","op"]
a["ts"] = pd.to_datetime(a.ts, format="%m/%d/%Y, %I:%M:%S.%f %p") + pd.Timedelta(hours=7)  # ke WIB
a = a.sort_values("ts").reset_index(drop=True)

runs = []
for f, sess in [("raw_20260912_024306.csv","sintetis"),("ext_20261016_025842.csv","eksternal"),
                ("ext_20261017_014519.csv","rerun")]:
    d = pd.read_csv(f); d = d[d.pattern=="S4"].copy(); d["session"]=sess
    d["fn"] = d.raw_status.str.extract(r"fnms=([\d.]+)").astype(float)
    runs.append(d)
r = pd.concat(runs, ignore_index=True)
r["ts"] = pd.to_datetime(r.timestamp)
r = r.sort_values("ts").reset_index(drop=True)
print("run S4 per sesi:", r.groupby("session").size().to_dict())

m = pd.merge_asof(r, a.rename(columns={"ts":"ts_appi"}), left_on="ts", right_on="ts_appi",
                  direction="nearest", tolerance=pd.Timedelta(seconds=3))
m["gap_s"] = (m.ts - m.ts_appi).dt.total_seconds()
ok = m.dropna(subset=["duration"])
print("terpasang:", ok.groupby("session").size().to_dict(),
      " tidak terpasang:", m[m.duration.isna()].groupby("session").size().to_dict())
print("gap (s) min/median/max:", ok.gap_s.min(), ok.gap_s.median(), ok.gap_s.max())
print("duplikat request terpakai:", ok.ts_appi.duplicated().sum())
print("fail:", (ok.success!=True).sum())

# per sesi tanggal di appi
a["date"]=a.ts.dt.date
print("\nrequest appi per tanggal WIB:", a.groupby("date").size().to_dict())

meas = ok[ok.phase=="measure"].copy()
meas["overhead"] = meas.duration - meas.fn
g = meas.groupby(["session","source","scale"]).agg(n=("duration","size"),
        appi_p50=("duration","median"), fn_p50=("fn","median"),
        overhead_p50=("overhead","median"), rt_p50=("roundtrip_ms","median")).reset_index()
print(g.round(1).to_string(index=False))
print("\nkorelasi Spearman duration vs fn_ms:", meas[["duration","fn"]].corr("spearman").iloc[0,1].round(3))
print("overhead median per sumber:", meas.groupby("source").overhead.median().round(1).to_dict())
g.to_csv("appi_s4_summary.csv", index=False)
m.to_csv("appi_s4_matched.csv", index=False)
