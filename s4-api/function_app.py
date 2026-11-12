import json
import os
import time

import azure.functions as func
import pyodbc
import requests

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

# Satu entri per target pengujian. Kunci = bagian skala dari parameter
# (mis. "5k" dari SQL_5k, "UCI5k" dari SQL_UCI5k).
# sql_where dan dv_filter berasal dari konfigurasi tetap, bukan dari input
# pengguna, sehingga aman disisipkan langsung ke query.
TARGETS = {
    # ---- dataset sintetis ----
    "5k":   {"sql": "TestDataset5k",   "sql_where": "Status = 'Selesai'",
             "dv": "cr626_testdatasets",     "dv_filter": "cr626_status eq 0"},
    "10k":  {"sql": "TestDataset10k",  "sql_where": "Status = 'Selesai'",
             "dv": "cr626_testdataset10ks",  "dv_filter": "cr626_status eq 547110001"},
    "25k":  {"sql": "TestDataset25k",  "sql_where": "Status = 'Selesai'",
             "dv": "cr626_testdataset25ks",  "dv_filter": "cr626_status eq 547110000"},
    "50k":  {"sql": "TestDataset50k",  "sql_where": "Status = 'Selesai'",
             "dv": "cr626_testdataset50ks",  "dv_filter": "cr626_status eq 547110000"},
    "100k": {"sql": "TestDataset100k", "sql_where": "Status = 'Selesai'",
             "dv": "cr626_testdataset100ks", "dv_filter": "cr626_status eq 547110000"},

    # ---- UCI Online Retail II ----
    "UCI5k":   {"sql": "UCI5k",   "sql_where": "Quantity >= 6",
                "dv": "cr626_uci5k_2s",   "dv_filter": "cr626_quantity ge 6"},
    "UCI10k":  {"sql": "UCI10k",  "sql_where": "Quantity >= 6",
                "dv": "cr626_uci10ks",  "dv_filter": "cr626_quantity ge 6"},
    "UCI50k":  {"sql": "UCI50k",  "sql_where": "Quantity >= 6",
                "dv": "cr626_uci50ks",  "dv_filter": "cr626_quantity ge 6"},
    "UCI100k": {"sql": "UCI100k", "sql_where": "Quantity >= 6",
                "dv": "cr626_uci100ks", "dv_filter": "cr626_quantity ge 6"},

    # ---- Olist ----
    "OLIST5k":   {"sql": "Olist5k",   "sql_where": "FreightValue >= 20",
                  "dv": "cr626_olist5ks",   "dv_filter": "cr626_freightvalue ge 20"},
    "OLIST10k":  {"sql": "Olist10k",  "sql_where": "FreightValue >= 20",
                  "dv": "cr626_olist10ks",  "dv_filter": "cr626_freightvalue ge 20"},
    "OLIST50k":  {"sql": "Olist50k",  "sql_where": "FreightValue >= 20",
                  "dv": "cr626_olist50ks",  "dv_filter": "cr626_freightvalue ge 20"},
    "OLIST100k": {"sql": "Olist100k", "sql_where": "FreightValue >= 20",
                  "dv": "cr626_olist100ks", "dv_filter": "cr626_freightvalue ge 20"},
}


def _dv_token():
    r = requests.post(
        f"https://login.microsoftonline.com/{os.environ['DV_TENANT']}/oauth2/v2.0/token",
        data={
            "grant_type": "client_credentials",
            "client_id": os.environ["DV_CLIENT_ID"],
            "client_secret": os.environ["DV_CLIENT_SECRET"],
            "scope": f"{os.environ['DV_URL'].rstrip('/')}/.default",
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def _query_sql(t):
    conn = pyodbc.connect(os.environ["SQL_CONN"])
    cur = conn.cursor()
    t0 = time.perf_counter()
    cur.execute(f"SELECT COUNT(*) FROM dbo.{t['sql']} WHERE {t['sql_where']}")
    rows = cur.fetchone()[0]
    elapsed = (time.perf_counter() - t0) * 1000
    cur.close()
    conn.close()
    return rows, elapsed


def _query_dataverse(t):
    base = os.environ["DV_URL"].rstrip("/")
    token = _dv_token()
    url = (f"{base}/api/data/v9.2/{t['dv']}"
           f"?$apply=filter({t['dv_filter']})/aggregate($count as jml)")
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
    }
    t0 = time.perf_counter()
    r = requests.get(url, headers=headers, timeout=180)
    r.raise_for_status()
    elapsed = (time.perf_counter() - t0) * 1000
    value = r.json().get("value", [])
    rows = value[0].get("jml", -1) if value else 0
    return rows, elapsed


@app.route(route="ping")
def ping(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps({"ok": True}), mimetype="application/json", status_code=200
    )


@app.route(route="query")
def query(req: func.HttpRequest) -> func.HttpResponse:
    source = (req.params.get("source") or "").upper()
    scale = req.params.get("scale") or ""

    if source not in ("SQL", "DV") or scale not in TARGETS:
        return func.HttpResponse(
            json.dumps({"error": f"source harus SQL/DV, scale harus salah satu dari "
                                 f"{sorted(TARGETS)}"}),
            mimetype="application/json", status_code=400,
        )

    t = TARGETS[scale]
    try:
        rows, elapsed = _query_sql(t) if source == "SQL" else _query_dataverse(t)
    except Exception as exc:
        return func.HttpResponse(
            json.dumps({"error": str(exc)}), mimetype="application/json", status_code=500
        )

    return func.HttpResponse(
        json.dumps({"rows": rows, "queryMs": round(elapsed, 2)}),
        mimetype="application/json", status_code=200,
    )