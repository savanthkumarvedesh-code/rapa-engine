from fares.collector import collect_route_fares
import json

res = collect_route_fares()
print(json.dumps(res["routes"], indent=2))