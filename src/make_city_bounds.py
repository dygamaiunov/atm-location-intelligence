# Разовая фиксация границ городов в docs/city_bounds.json

import json
import os

import pandas as pd

ATMS_PATH = "data/frozen/atms_all_cities.csv"
BOUNDS_PATH = "docs/city_bounds.json"
PADDING = 0.05

if os.path.exists(BOUNDS_PATH):
    raise ValueError(f"{BOUNDS_PATH} уже существует. Границы фиксируются один раз - если правда нужно пересоздать, удали файл руками")
if not os.path.exists(ATMS_PATH):
    raise ValueError(f"{ATMS_PATH} не найден. Положи atms_all_cities.csv в data/frozen/")

atms = pd.read_csv(ATMS_PATH)
print("Банкоматов в снапшоте:", atms.shape[0])
print("Города:", sorted(atms["city"].unique()))

bounds = {}
for city, city_atms in atms.groupby("city"):
    pad_lat = (city_atms["lat"].max() - city_atms["lat"].min()) * PADDING
    pad_lon = (city_atms["lon"].max() - city_atms["lon"].min()) * PADDING
    bounds[city] = {
        "lat_min": round(float(city_atms["lat"].min() - pad_lat), 6),
        "lat_max": round(float(city_atms["lat"].max() + pad_lat), 6),
        "lon_min": round(float(city_atms["lon"].min() - pad_lon), 6),
        "lon_max": round(float(city_atms["lon"].max() + pad_lon), 6)}
    print(f"{city}: {bounds[city]}")

with open(BOUNDS_PATH, "w", encoding="utf-8") as f:
    json.dump(bounds, f, ensure_ascii=False, indent=2)
print(f"Границы зафиксированы в {BOUNDS_PATH}")