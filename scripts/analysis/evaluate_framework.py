"""Evaluasi akhir decision framework: confusion matrix + F1 untuk 3 lapis validasi.

Keputusan yang dievaluasi (operasi dengan predikat delegable):
    "Apakah S1 (Filter delegable + ClearCollect) aman dipakai?"
    aman = hasil lengkap (completeness >= 0.999) DAN median roundtrip < SLA.
Kelas positif = "S1 TIDAK aman, harus pindah ke S3/S4".
Unit evaluasi = sel (skala x sumber data).

Lapis 1: LOSO pada data sintetis (skala 5k/10k/50k/100k, aturan dilatih dari 3 skala sisanya)
Lapis 2: holdout 25k sintetis (aturan dilatih dari 4 skala)
Lapis 3: eksternal UCI + Olist (aturan dilatih dari 4 skala sintetis)
"""
import pandas as pd, numpy as np

SLA, LIMIT = 2000, 2000
SYNTH = "raw_20260912_024306.csv"
EXT_GT = "ext_ground_truth.csv"           # keluaran validate_external.py
SELREP = "selectivity_report.csv"

# ---------- data sintetis ----------
syn = pd.read_csv(SYNTH)
syn = syn[(syn.phase=="measure") & syn.raw_status.str.startswith("DONE") & (syn.pattern=="S1")]
EXP = {"5k":984,"10k":1925,"25k":4962,"50k":10040,"100k":20056}
N   = {"5k":5000,"10k":10000,"25k":25000,"50k":50000,"100k":100000}
S_SYN = 0.20
ss = syn.groupby(["source","scale"]).agg(med=("roundtrip_ms","median"), rows=("rows","median")).reset_index()
ss["comp"] = ss.rows / ss.scale.map(EXP)
ss["truth_safe"] = (ss.comp >= 0.999) & (ss.med < SLA)
ss["V"] = ss.scale.map(N); ss["s"] = S_SYN
dv = ss[ss.source=="DV"].set_index("scale")

def fit(train):
    """Latih ambang latency dan empiris dari skala train (kurva S1 DV)."""
    tr = sorted(train, key=N.get); y = np.array([dv.loc[t,"med"] for t in tr]); best = (np.inf, None)
    for k in range(2, len(y)-1):
        rss = ((y[:k]-y[:k].mean())**2).sum() + ((y[k:]-y[k:].mean())**2).sum()
        if rss < best[0]: best = (rss, N[tr[k]])
    T_lat = best[1] or max(N[t] for t in tr)
    ok = [t for t in tr if dv.loc[t,"truth_safe"]]
    T_emp = max(N[t] for t in ok) if ok else 0
    return T_lat, T_emp

def predict(df, T_lat, T_emp):
    out = df.copy()
    out["latency"]    = out.V <  T_lat
    out["empiris"]    = out.V <= T_emp
    out["mekanistik"] = out.V * out.s <= LIMIT
    return out

# lapis 1: LOSO
train4 = ["5k","10k","50k","100k"]
loso = []
for held in train4:
    T_lat, T_emp = fit([t for t in train4 if t != held])
    loso.append(predict(ss[ss.scale==held], T_lat, T_emp).assign(T_lat=T_lat, T_emp=T_emp))
loso = pd.concat(loso)
# lapis 2: holdout 25k
T_lat4, T_emp4 = fit(train4)
hold = predict(ss[ss.scale=="25k"], T_lat4, T_emp4)

# lapis 3: eksternal. selektivitas diestimasi dari sampel 5k (skenario realistis:
# developer mengukur selektivitas pada subset kecil, lalu menerapkannya ke volume lebih besar)
sel = pd.read_csv(SELREP)
S_EST = {d.upper(): g.loc[g.skala.idxmin(), "selectivity_pct"]/100 for d, g in sel.groupby("dataset")}
ext = pd.read_csv(EXT_GT)
ext["s"] = ext.dataset.map(S_EST)
ext = predict(ext, T_lat4, T_emp4)

# ---------- metrik ----------
RULES = ["latency","empiris","mekanistik"]
def cm(df, rule):
    pos_true = ~df.truth_safe; pos_pred = ~df[rule]
    TP = int(( pos_true &  pos_pred).sum()); FN = int(( pos_true & ~pos_pred).sum())
    FP = int((~pos_true &  pos_pred).sum()); TN = int((~pos_true & ~pos_pred).sum())
    prec = TP/(TP+FP) if TP+FP else np.nan; rec = TP/(TP+FN) if TP+FN else np.nan
    f1 = 2*prec*rec/(prec+rec) if (prec==prec and rec==rec and prec+rec) else (np.nan if TP+FN==0 else 0.0)
    return dict(TP=TP, FN=FN, FP=FP, TN=TN, n=len(df), accuracy=(TP+TN)/len(df),
                precision=prec, recall=rec, F1=f1,
                FNR=FN/(TP+FN) if TP+FN else np.nan, FPR=FP/(FP+TN) if FP+TN else np.nan)

rows = []
for layer, df in [("1. LOSO sintetis", loso), ("2. Holdout 25k sintetis", hold),
                  ("3. Eksternal UCI+Olist", ext)]:
    for r in RULES:
        rows.append(dict(lapis=layer, aturan=r, **cm(df, r)))
res = pd.DataFrame(rows)
pd.set_option("display.width", 200)
print(f"Ambang (dilatih 4 skala sintetis): latency V < {T_lat4}, empiris V <= {T_emp4}")
print(f"Ambang LOSO latency per fold: {loso.groupby('scale').T_lat.first().to_dict()}")
print(f"Selektivitas estimasi (sampel 5k): {S_EST}\n")
print(res.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
res.to_csv("framework_confusion_f1.csv", index=False)

# gabungan semua lapis
tot = pd.concat([loso, hold, ext])
print("\nGabungan 3 lapis:")
for r in RULES:
    print(" ", r, {k: (round(v,3) if isinstance(v,float) else v) for k,v in cm(tot, r).items()})

# sel yang salah diprediksi
print("\nSel salah prediksi:")
for layer, df in [("LOSO", loso), ("Holdout", hold), ("Eksternal", ext)]:
    for r in RULES:
        w = df[df[r] != df.truth_safe]
        for x in w.itertuples():
            print(f"  [{layer}] {r:10s} {x.source} {x.scale}: truth_safe={x.truth_safe} pred_safe={getattr(x, r)}")

# ---------- sensitivitas selektivitas ----------
print("\nSensitivitas: rentang s yang membuat prediksi mekanistik tetap benar di tiap sel eksternal")
for x in ext.drop_duplicates("scale").itertuples():
    s_crit = LIMIT / x.V
    print(f"  {x.scale:10s} V={x.V:6d}  s_kritis={s_crit:.3f}  s_aktual={x.true_rows/x.V:.3f}  "
          f"margin={'aman' if x.truth_safe else 'terpotong'} ({(x.true_rows/x.V - s_crit):+.3f})")
