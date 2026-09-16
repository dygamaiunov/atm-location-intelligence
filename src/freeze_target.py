# Заморозка таргета: привязка банкоматов 2ГИС-снапшота к ячейкам сетки

import json
import os
import numpy as np
import pandas as pd

from src.config import CELL_SIZE_M, GRID_VERSION, TARGET_SNAPSHOT_DATE, CITY_CODES

ATMS_PATH = "data/frozen/atms_all_cities.csv"
BOUNDS_PATH = "docs/city_bounds.json"
GRID_PATH = f"data/processed/grid_{GRID_VERSION}.parquet"
TARGET_PATH = f"data/frozen/target_2gis_{TARGET_SNAPSHOT_DATE}_grid_{GRID_VERSION}.parquet"
METERS_PER_DEG_LAT = 111320.0

BANK_COLUMNS = {
    "Сбербанк": "sber_count",
    "Тинькофф": "tinkoff_count",
    "ВТБ": "vtb_count",
    "Альфа-Банк": "alfa_count",
    "Газпромбанк": "gazprom_count",
    "Райффайзен": "raiff_count"}

if not os.path.exists(ATMS_PATH):
    raise ValueError(f"{ATMS_PATH} не найден. Необходимо положить atms_all_cities.csv в data/frozen/")
if not os.path.exists(GRID_PATH):
    raise ValueError(f"{GRID_PATH} не найден. Сначала сгенерируй сетку src.make_grid")

atms = pd.read_csv(ATMS_PATH)
grid = pd.read_parquet(GRID_PATH)
with open(BOUNDS_PATH, encoding="utf-8") as f:
    bounds = json.load(f)

atms_total = atms.shape[0]
print(f"Сетка: {GRID_PATH}, ячеек {grid.shape[0]}")
print("Банкоматов в снапшоте:", atms_total)
print("Банки в снапшоте:", sorted(atms["bank"].unique()))

unknown_banks = set(atms["bank"].unique()) - set(BANK_COLUMNS)
if unknown_banks:
    raise ValueError(f"В снапшоте банки, которых нет в BANK_COLUMNS: {unknown_banks}")

# привязка каждого банкомата к ячейке по формуле сетки
atm_cell_ids = []
for city, city_atms in atms.groupby("city"):
    city_bounds = bounds[city]
    step_lat = CELL_SIZE_M / METERS_PER_DEG_LAT
    mid_lat = (city_bounds["lat_min"] + city_bounds["lat_max"]) / 2
    step_lon = CELL_SIZE_M / (METERS_PER_DEG_LAT * np.cos(np.radians(mid_lat)))

    rows = np.floor((city_atms["lat"].values - city_bounds["lat_min"]) / step_lat).astype(int)
    cols = np.floor((city_atms["lon"].values - city_bounds["lon_min"]) / step_lon).astype(int)

    code = CITY_CODES[city]
    cell_ids = pd.Series(
        [f"{code}_{r}_{c}" for r, c in zip(rows, cols)],
        index=city_atms.index)
    atm_cell_ids.append(cell_ids)

atms["cell_id"] = pd.concat(atm_cell_ids)

# банкоматы, не попавшие в существующую ячейку сетки, - за пределами административного bbox
outside = ~atms["cell_id"].isin(grid["cell_id"])
print(f"\nЗа пределами сетки: {int(outside.sum())} банкоматов ({outside.mean():.1%} снапшота)")
if outside.any():
    print(pd.crosstab(atms.loc[outside, "city"], atms.loc[outside, "bank"], margins=True, margins_name="Итого").to_string())
atms = atms[~outside]

# агрегация в счётчики по ячейкам
target = atms.pivot_table(index="cell_id", columns="bank", aggfunc="size", fill_value=0)
target = target.reindex(columns=list(BANK_COLUMNS), fill_value=0)
target = target.rename(columns=BANK_COLUMNS).reset_index()
target.columns.name = None
target["atm_count"] = target[list(BANK_COLUMNS.values())].sum(axis=1)

target.to_parquet(TARGET_PATH, index=False)

print(f"\nЯчеек с банкоматами: {target.shape[0]} из {grid.shape[0]} ({target.shape[0] / grid.shape[0]:.1%} сетки)")
for bank, column in BANK_COLUMNS.items():
    cells_with_bank = int((target[column] > 0).sum())
    print(f"{bank}: {int(target[column].sum())} банкоматов в {cells_with_bank} ячейках")
print("Контрольная сумма:", int(target["atm_count"].sum()), "== в сетке:", atms.shape[0],
      "| в сетке + за пределами == снапшот:", atms.shape[0] + int(outside.sum()), "==", atms_total)
print(f"Таргет заморожен: {TARGET_PATH}")