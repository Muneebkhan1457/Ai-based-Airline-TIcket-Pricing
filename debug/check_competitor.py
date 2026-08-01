import sqlite3
conn = sqlite3.connect('Data_load/flight.db')
print('=== Competitor signals per route ===')
rows = conn.execute(
    "SELECT route, signal_type, value FROM external_signals "
    "WHERE signal_type LIKE 'competitor_price_%' ORDER BY route, signal_type"
).fetchall()
for r in rows:
    print(f'  route={str(r[0]):<10}  type={r[1]:<22}  value={r[2]}')
print()
print('=== get_competitor_stats result ===')
for route in ['KHI-LHE', 'KHI-ISB', 'KHI-PEW', 'LHE-ISB', 'KHI-DXB']:
    vals = [r[0] for r in conn.execute(
        "SELECT value FROM external_signals WHERE route=? AND signal_type LIKE 'competitor_price_%'",
        (route,)
    ).fetchall()]
    if vals:
        print(f'  {route}: min={min(vals):.2f}  avg={sum(vals)/len(vals):.2f}  n={len(vals)}  -> ceiling={sum(vals)/len(vals)*1.15:.2f} PKR')
    else:
        print(f'  {route}: NO competitor data -> guardrail ceiling inactive')
conn.close()
