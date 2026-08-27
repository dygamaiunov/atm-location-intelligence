# Генерация стабильной сетки из зафиксированных границ

import json
import numpy as np
import pandas as pd

from src.config import CELL_SIZE_M, GRID_VERSION

BOUNDS_PATH = "docs/city_bounds.json"
GRID_PATH = f"data/processed/grid_{GRID_VERSION}.parquet"
METERS_PER_DEG_LAT = 111320.0

CITY_CODES = {"Москва": "msk", "Санкт-Петербург": "spb", "Нижний Новгород": "nnov", 
              "Новосибирск": "nsk", "Казань": "kzn"}

with open(BOUNDS_PATH, encoding="utf-8") as f:
    bounds = json.load(f)

frames = []
for city, city_bounds in bounds.items():
    step_lat = CELL_SIZE_M / METERS_PER_DEG_LAT
    # шаг по долготе зависит от широты города: клетки остаются приближенно квадратными в метрах
    mid_lat = (city_bounds["lat_min"] + city_bounds["lat_max"]) / 2
    step_lon = CELL_SIZE_M / (METERS_PER_DEG_LAT * np.cos(np.radians(mid_lat)))

    lat_centers = np.arange(city_bounds["lat_min"] + step_lat / 2, city_bounds["lat_max"], step_lat)
    lon_centers = np.arange(city_bounds["lon_min"] + step_lon / 2, city_bounds["lon_max"], step_lon)

    rows, cols = np.meshgrid(np.arange(len(lat_centers)), np.arange(len(lon_centers)), indexing="ij")
    lats, lons = np.meshgrid(lat_centers, lon_centers, indexing="ij")

    code = CITY_CODES[city]
    df = pd.DataFrame({
        "cell_id": [f"{code}_{r}_{c}" for r, c in zip(rows.ravel(), cols.ravel())],
        "city": city,
        "lat": lats.ravel().round(6),
        "lon": lons.ravel().round(6)})
    frames.append(df)
    print(f"{city}: {len(lat_centers)} x {len(lon_centers)} = {df.shape[0]} ячеек")

grid = pd.concat(frames, ignore_index=True)
if grid["cell_id"].duplicated().any():
    raise ValueError("Найдены дубли cell_id - проверь границы городов в city_bounds.json")

grid.to_parquet(GRID_PATH, index=False)
print(f"Итого ячеек: {grid.shape[0]}, сохранено в {GRID_PATH}")