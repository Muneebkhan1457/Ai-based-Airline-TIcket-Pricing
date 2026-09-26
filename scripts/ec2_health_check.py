#!/usr/bin/env python3
"""
Comprehensive EC2 system health check.
Run on the EC2 server: python3 /tmp/ec2_health_check.py
"""
import json
import sys
import requests

API = "http://localhost:8000"
PASS = "\033[92m[PASS]\033[0m"
FAIL = "\033[91m[FAIL]\033[0m"
WARN = "\033[93m[WARN]\033[0m"
INFO = "\033[94m[INFO]\033[0m"

results = []

def check(name, ok, detail=""):
    status = PASS if ok else FAIL
    print(f"{status} {name}")
    if detail:
        print(f"       {detail}")
    results.append((name, ok))

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

# ─────────────────────────────────────────────
section("1. API HEALTH")
# ─────────────────────────────────────────────
try:
    r = requests.get(f"{API}/health", timeout=10)
    d = r.json()
    check("GET /health → 200", r.status_code == 200, json.dumps(d))
    check("database_connected", d.get("database_connected") is True)
    check("model_loaded", d.get("model_loaded") is True)
except Exception as e:
    check("GET /health", False, str(e))

# ─────────────────────────────────────────────
section("2. PRICING / RECOMMEND")
# ─────────────────────────────────────────────
payload = {
    "route": "KHI-LHE",
    "flight_class": "Economy",
    "days_to_departure": 14,
    "total_seats": 180,
    "remaining_seats": 90,
}
try:
    r = requests.post(f"{API}/pricing/recommend", json=payload, timeout=40)
    check("POST /pricing/recommend → 200", r.status_code == 200, r.text[:300])
    if r.status_code == 200:
        d = r.json()
        check("  recommended_price present", "recommended_price" in d, str(d.get("recommended_price")))
        check("  expected_revenue present", "expected_revenue" in d, str(d.get("expected_revenue")))
        check("  predicted_demand_ratio present", "predicted_demand_ratio" in d, str(d.get("predicted_demand_ratio")))
        check("  competitor_data_is_real present", "competitor_data_is_real" in d, str(d.get("competitor_data_is_real")))
except Exception as e:
    check("POST /pricing/recommend", False, str(e))

# ─────────────────────────────────────────────
section("3. PRICING / HISTORY / LATEST")
# ─────────────────────────────────────────────
try:
    r = requests.get(f"{API}/pricing/history/latest", timeout=10)
    check("GET /pricing/history/latest → 200", r.status_code == 200)
    if r.status_code == 200:
        d = r.json()
        check("  Returns a list", isinstance(d, list), f"count={len(d)}")
        if d:
            sample = d[0]
            check("  Item has 'route'", "route" in sample)
            check("  Item has 'price'", "price" in sample)
            check("  Item has 'recorded_at'", "recorded_at" in sample)
            print(f"       Sample row: {json.dumps(sample)}")
except Exception as e:
    check("GET /pricing/history/latest", False, str(e))

# ─────────────────────────────────────────────
section("4. SIGNALS / HISTORY")
# ─────────────────────────────────────────────
try:
    r = requests.get(f"{API}/signals/history", timeout=10)
    check("GET /signals/history → 200", r.status_code == 200)
    if r.status_code == 200:
        d = r.json()
        check("  Returns a list", isinstance(d, list), f"count={len(d)}")
        if d:
            sample = d[0]
            check("  Item has 'signal_type'", "signal_type" in sample)
            print(f"       Sample signal: {json.dumps(sample)}")
except Exception as e:
    check("GET /signals/history", False, str(e))

# ─────────────────────────────────────────────
section("5. PRICING / PREDICT-DEMAND-AT-PRICE")
# ─────────────────────────────────────────────
payload2 = {
    "route": "KHI-ISB",
    "flight_class": "Business",
    "days_to_departure": 7,
    "price": 25000,
}
try:
    r = requests.post(f"{API}/pricing/predict-demand-at-price", json=payload2, timeout=30)
    check("POST /pricing/predict-demand-at-price → 200", r.status_code == 200, r.text[:200])
    if r.status_code == 200:
        d = r.json()
        check("  predicted_demand_ratio present", "predicted_demand_ratio" in d, str(d.get("predicted_demand_ratio")))
except Exception as e:
    check("POST /pricing/predict-demand-at-price", False, str(e))

# ─────────────────────────────────────────────
section("6. BATCH REPRICE (full end-to-end)")
# ─────────────────────────────────────────────
print(f"{INFO} Running batch reprice — this may take 1-3 minutes...")
try:
    r = requests.post(f"{API}/pricing/batch-reprice", timeout=300)
    check("POST /pricing/batch-reprice → 200", r.status_code == 200, r.text[:400])
    if r.status_code == 200:
        d = r.json()
        check("  'message' in response", "message" in d, d.get("message", ""))
        check("  'results' in response", "results" in d or "prices" in d or len(d) > 0, str(list(d.keys())))
except Exception as e:
    check("POST /pricing/batch-reprice", False, str(e))

# ─────────────────────────────────────────────
section("7. ETL TRIGGER (signals/trigger-etl)")
# ─────────────────────────────────────────────
print(f"{INFO} Triggering ETL — scrapes live competitor/fuel data...")
try:
    r = requests.post(f"{API}/signals/trigger-etl", timeout=120)
    check("POST /signals/trigger-etl → 200", r.status_code == 200, r.text[:300])
except Exception as e:
    check("POST /signals/trigger-etl", False, str(e))

# ─────────────────────────────────────────────
section("SUMMARY")
# ─────────────────────────────────────────────
total = len(results)
passed = sum(1 for _, ok in results if ok)
failed = total - passed
print(f"\n  Total checks : {total}")
print(f"  Passed       : \033[92m{passed}\033[0m")
print(f"  Failed       : \033[91m{failed}\033[0m")
if failed == 0:
    print(f"\n{PASS} ALL SYSTEMS OPERATIONAL\n")
else:
    print(f"\n{FAIL} {failed} CHECK(S) FAILED — review output above\n")
    sys.exit(1)
