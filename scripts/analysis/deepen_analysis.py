"""Analisis pendalaman: effect size RM2, sign test, model analitis truncation, sensitivitas framework."""
import pandas as pd, numpy as np
from scipy.stats import mannwhitneyu, binomtest
rng = np.random.default_rng(42)

def load(p):
    d = pd.read_csv(p); return d[(d.phase=="measure") & d.raw_status.str.startswith("DONE")]
syn = load("raw_20260912_024306.csv")
main, rr = load("ext_20261016_025842.csv"), load("ext_20261017_014519.csv")
T = {("S1","SQL","OLIST10k"),("S1","SQL","OLIST5k"),("S2","SQL","UCI5k"),("S2","SQL","OLIST10k")}
k = lambda d: [x in T for x in zip(d.pattern,d.source,d.scale)]
ext = pd.concat([main[[not x for x in k(main)]], rr[k(rr)]])
order = ["5k","10k","25k","50k","100k","UCI5k","UCI10k","UCI50k","UCI100k","OLIST5k","OLIST10k","OLIST50k","OLIST100k"]

# ---------- 1. RM2 effect size ----------
def hl_boot(a, b, B=5000):
    """Hodges-Lehmann shift (median of pairwise diffs) + bootstrap 95% CI of median difference."""
    hl = np.median(np.subtract.outer(a, b))
    bs = [np.median(rng.choice(a, len(a))) - np.median(rng.choice(b, len(b))) for _ in range(B)]
    return hl, np.percentile(bs, 2.5), np.percentile(bs, 97.5)

rows = []
for name, d in [("sintetis", syn), ("eksternal", ext)]:
    for (p, sc), g in d.groupby(["pattern","scale"]):
        a = g[g.source=="DV"].roundtrip_ms.values; b = g[g.source=="SQL"].roundtrip_ms.values
        if len(a) < 3 or len(b) < 3: continue
        U, pv = mannwhitneyu(a, b, alternative="two-sided")
        r_rb = 1 - 2*U/(len(a)*len(b))            # rank-biserial = Cliff's delta (SQL lebih lambat bila > 0)
        hl, lo, hi = hl_boot(a, b)
        rows.append(dict(data=name, pattern=p, scale=sc, med_DV=np.median(a), med_SQL=np.median(b),
                         HL_shift=hl, CI_lo=lo, CI_hi=hi, U=U, p=pv, cliffs_delta=r_rb,
                         dv_faster=np.median(a) < np.median(b)))
rm2 = pd.DataFrame(rows)
rm2["mag"] = pd.cut(rm2.cliffs_delta.abs(), [-1,0.147,0.33,0.474,1.01], labels=["negligible","small","medium","large"])
rm2 = rm2.sort_values(["data","pattern","scale"], key=lambda c: c.map({v:i for i,v in enumerate(order)}) if c.name=="scale" else c)
rm2.round(3).to_csv("rm2_effect_size.csv", index=False)
print("=== RM2 effect size ===")
print(rm2.round(3).to_string(index=False))
for name in ["sintetis","eksternal"]:
    x = rm2[rm2.data==name]; n = len(x); w = int(x.dv_faster.sum())
    print(f"sign test {name}: DV lebih cepat di {w}/{n} sel, p = {binomtest(w, n, 0.5).pvalue:.2e}")
x = rm2; w = int(x.dv_faster.sum()); print(f"sign test gabungan: {w}/{len(x)}, p = {binomtest(w, len(x), .5).pvalue:.2e}")
print("min p Mann-Whitney mungkin (n=5 vs 5):", 2/252)

# ---------- 2. model analitis truncation ----------
EXP = {"5k":984,"10k":1925,"25k":4962,"50k":10040,"100k":20056}
TRUE = {"UCI5k":1985,"UCI10k":3912,"UCI50k":19547,"UCI100k":39359,"OLIST5k":1388,"OLIST10k":2800,"OLIST50k":13953,"OLIST100k":27886}
S = {"syn":0.20, "UCI":0.397, "OLIST":0.2776}
def ds(sc): return "UCI" if sc.startswith("UCI") else "OLIST" if sc.startswith("OLIST") else "syn"
mrows = []
for name, d, true in [("sintetis", syn, EXP), ("eksternal", ext, TRUE)]:
    for (p, src, sc), g in d[d.pattern.isin(["S1","S2"])].groupby(["pattern","source","scale"]):
        obs = g.rows.median(); t = true[sc]
        pred = min(t, 2000) if p=="S1" else S[ds(sc)]*2000
        mrows.append(dict(data=name, pattern=p, source=src, scale=sc, true_rows=t, pred=round(pred), obs=obs,
                          err_pct=(obs-pred)/pred*100))
mod = pd.DataFrame(mrows).sort_values(["pattern","data","scale","source"], key=lambda c: c.map({v:i for i,v in enumerate(order)}) if c.name=="scale" else c)
mod.round(2).to_csv("truncation_model.csv", index=False)
print("\n=== Model analitis truncation ===")
print(mod.round(2).to_string(index=False))
for p in ["S1","S2"]:
    e = mod[mod.pattern==p].err_pct.abs()
    print(f"{p}: n={len(e)}, MAPE={e.mean():.2f}%, max |err|={e.max():.2f}%")

# ---------- 3. sensitivitas framework ----------
# truth per sel S1: lengkap & median < SLA; prediksi mekanistik V*s_est <= k*2000
cells = []
for name, d, true, V in [("sintetis", syn, EXP, {"5k":5000,"10k":10000,"25k":25000,"50k":50000,"100k":100000}),
                         ("eksternal", ext, TRUE, {k_:int(k_.replace("UCI","").replace("OLIST","").replace("k",""))*1000 for k_ in TRUE})]:
    for (src, sc), g in d[d.pattern=="S1"].groupby(["source","scale"]):
        cells.append(dict(data=name, source=src, scale=sc, V=V[sc], s=S[ds(sc)], comp=g.rows.median()/true[sc],
                          med=g.roundtrip_ms.median()))
c = pd.DataFrame(cells)
def evalrule(sla, kfac, s_err):
    truth = (c.comp >= .999) & (c.med < sla)
    pred = c.V * c.s * (1+s_err) <= kfac*2000
    pos_t, pos_p = ~truth, ~pred
    TP=(pos_t&pos_p).sum(); FN=(pos_t&~pos_p).sum(); FP=(~pos_t&pos_p).sum(); TN=(~pos_t&~pos_p).sum()
    f1 = 2*TP/(2*TP+FP+FN) if TP+FP+FN else np.nan
    return dict(SLA_ms=sla, margin_k=kfac, s_error=f"{s_err:+.0%}", acc=(TP+TN)/len(c), F1=f1, FN=int(FN), FP=int(FP), n=len(c))
sens = [evalrule(sla,1.0,0) for sla in (500,750,1000,1500,2000,3000)]
sens += [evalrule(2000,1.0,e) for e in (-0.2,-0.1,0.05,0.1,0.2)]
sens += [evalrule(2000,kf,0) for kf in (0.9,0.8)]
sens += [evalrule(2000,0.9,e) for e in (0.1,-0.1)]
sens = pd.DataFrame(sens)
sens.round(3).to_csv("framework_sensitivity.csv", index=False)
print("\n=== Sensitivitas (n sel S1 sintetis+eksternal) ===")
print(sens.round(3).to_string(index=False))
# sel mana yang salah pada skenario kunci
for sla,kf,e in [(1000,1,0),(750,1,0),(2000,1,0.05),(2000,1,-0.2),(2000,0.9,0)]:
    truth = (c.comp >= .999) & (c.med < sla); pred = c.V*c.s*(1+e) <= kf*2000
    w = c[truth != pred]
    print(f"  SLA={sla} k={kf} err={e:+.0%}: salah ->", list(zip(w.source, w.scale)))
