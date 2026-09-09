from fares.live_scraper import fetch_live_fares_calibrated, try_aviasales_api

# Test DEL-BOM T+45 (SpiceJet was showing 6264 vs actual 6528)
quotes = fetch_live_fares_calibrated('DEL', 'BOM', '2026-10-24', 'T+45')
print(f'DEL-BOM T+45 ({len(quotes)} quotes):')
for q in quotes:
    print(f'  {q.carrier_code} {q.flight_number}: INR {q.total_fare}')

print()
quotes_t1 = fetch_live_fares_calibrated('DEL', 'BOM', '2026-09-10', 'T+1')
print(f'DEL-BOM T+1 last-minute ({len(quotes_t1)} quotes):')
for q in quotes_t1[:4]:
    print(f'  {q.carrier_code} {q.flight_number}: INR {q.total_fare}')

print()
print('Attempting Aviasales live API...')
live = try_aviasales_api('DEL', 'BOM', '2026-10-24', 'T+45')
if live:
    print(f'Got {len(live)} live quotes from Aviasales!')
else:
    print('No Aviasales data - calibrated anchors will be used instead')
