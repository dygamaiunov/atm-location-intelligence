# фиксация границ городов в docs/city_bounds.json
# Границы = bbox административной границы города в OSM (не координаты банкоматов)

import json
import math
import os
import time
import urllib.parse
import urllib.request
from datetime import date

from src.config import CITIES

BOUNDS_PATH = "docs/city_bounds.json"
NOMINATIM_URL = "https://nominatim.openstreetmap.org"
USER_AGENT = "atm-location-intelligence/0.1 (github.com/dygamaiunov/atm-location-intelligence)"

# 102269 - город федерального значения целиком (административная единица); 337422 - субъект целиком
RELATION_OVERRIDES = {"Москва": 102269, "Санкт-Петербург": 337422}

ACCEPTED_KINDS = {("boundary", "administrative"), ("place", "city")}

if os.path.exists(BOUNDS_PATH):
    raise ValueError(f"{BOUNDS_PATH} уже существует. Границы фиксируются один раз - если правда нужно пересоздать, удали файл руками")


def nominatim(endpoint, params):
    params = {**params, "format": "jsonv2", "accept-language": "ru"}
    url = f"{NOMINATIM_URL}/{endpoint}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        result = json.loads(response.read().decode("utf-8"))
    time.sleep(1.1)
    return result


def bbox_size_km(r):
    lat_min, lat_max, lon_min, lon_max = map(float, r["boundingbox"])
    height = (lat_max - lat_min) * 111.32
    width = (lon_max - lon_min) * 111.32 * math.cos(math.radians((lat_min + lat_max) / 2))
    return height, width


bounds = {}
for city in CITIES:
    print(f"=== {city} ===")
    candidates = [r for r in nominatim("search", {"city": city, "country": "Россия", "limit": 10})
                  if r.get("osm_type") == "relation"
                  and (r.get("category"), r.get("type")) in ACCEPTED_KINDS]
    for r in candidates:
        h, w = bbox_size_km(r)
        print(f"    найден relation {r['osm_id']} [{r['category']}/{r['type']}]: {r['display_name']}, ~{h:.0f} x {w:.0f} км")

    if city in RELATION_OVERRIDES:
        relation_id = RELATION_OVERRIDES[city]
        found = nominatim("lookup", {"osm_ids": f"R{relation_id}"})
        if not found:
            raise ValueError(f"{city}: relation {relation_id} из RELATION_OVERRIDES не найден в Nominatim")
        best = found[0]
        print(f"    по RELATION_OVERRIDES взят relation {relation_id}")
    elif candidates:
        best = candidates[0]  # Nominatim сортирует по значимости
    else:
        raise ValueError(f"{city}: Nominatim не вернул подходящий relation - пришли вывод, подберём relation вручную")

    lat_min, lat_max, lon_min, lon_max = map(float, best["boundingbox"])
    h, w = bbox_size_km(best)
    bounds[city] = {
        "lat_min": round(lat_min, 6),
        "lat_max": round(lat_max, 6),
        "lon_min": round(lon_min, 6),
        "lon_max": round(lon_max, 6),
        "osm_relation_id": best["osm_id"],
        "osm_name": best["display_name"],
        "fixed_on": date.today().isoformat()}
    print(f"    ИТОГ: relation {best['osm_id']}, lat {lat_min:.3f}..{lat_max:.3f}, "
          f"lon {lon_min:.3f}..{lon_max:.3f}, ~{h:.0f} x {w:.0f} км")

with open(BOUNDS_PATH, "w", encoding="utf-8") as f:
    json.dump(bounds, f, ensure_ascii=False, indent=2)
print(f"Границы зафиксированы в {BOUNDS_PATH}")