# Здесь происходит заморозка таргета: привязка банкоматов 2ГИС-снапшота к ячейкам сетки v2.

import json
import os
import numpy as np
import pandas as pd

from src.config import CELL_SIZE_M, GRID_VERSION, TARGET_SNAPSHOT_DATE, CITY_CODES

ATMS_PATH = "data/frozen/atms_all_cities.csv"
BOUNDS_PATH = "docs/city_bounds.json"
GRID_PATH = f"data/processed/grid_{GRID_VERSION}.parquet"
TARGET_PATH = f"data/frozen/target_2gis_{TARGET_SNAPSHOT_DATE}.parquet"
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
    raise ValueError(f"{GRID_PATH} не найден. Сначала необходимо сгенерировать сетку: python -m src.make_grid")

atms = pd.read_csv(ATMS_PATH)
grid = pd.read_parquet(GRID_PATH)
with open(BOUNDS_PATH, encoding="utf-8") as f:
    bounds = json.load(f)

print("Банкоматов в снапшоте:", atms.shape[0])
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
    cell_ids = pd.Series([f"{code}_{r}_{c}" for r, c in zip(rows, cols)], index=city_atms.index)
    atm_cell_ids.append(cell_ids)

atms["cell_id"] = pd.concat(atm_cell_ids)

# проверим, что каждый банкомат попал в существующую ячейку сетки
outside = ~atms["cell_id"].isin(grid["cell_id"])
if outside.any():
    raise ValueError(f"{outside.sum()} банкоматов не попали в сетку - проверь, что границы и CELL_SIZE_M не менялись с генерации")

# агрегация в счётчики по ячейкам
target = atms.pivot_table(index="cell_id", columns="bank", aggfunc="size", fill_value=0)
# банк без банкоматов в снапшоте получит колонку из нулей, а не KeyError
target = target.reindex(columns=list(BANK_COLUMNS), fill_value=0)
target = target.rename(columns=BANK_COLUMNS).reset_index()
target.columns.name = None
target["atm_count"] = target[list(BANK_COLUMNS.values())].sum(axis=1)

target.to_parquet(TARGET_PATH, index=False)

print("Ячеек с банкоматами:", target.shape[0])
for bank, column in BANK_COLUMNS.items():
    cells_with_bank = int((target[column] > 0).sum())
    print(f"{bank}: {int(target[column].sum())} банкоматов в {cells_with_bank} ячейках")
print("Контрольная сумма:", int(target["atm_count"].sum()), "== число банкоматов снапшота:", atms.shape[0])
print(f"Таргет заморожен: {TARGET_PATH}")