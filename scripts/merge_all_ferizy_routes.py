#!/usr/bin/env python3
"""Merge Trip and Classic Ferizy routes into one normalized route CSV."""
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPORTS = ROOT / "exports"

FIELDS = [
    "routeId", "source", "originHarbourId", "destinationHarbourId",
    "originHarbourName", "originProvince", "origin", "destination",
    "destinationProvince", "shipClassId", "shipClass",
]
PORT_PROVINCES = {
    "2": "Banten", "3": "Lampung", "4": "Bali", "5": "Jawa Timur",
}


def read(path: Path):
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def trip_rows():
    for row in read(EXPORTS / "routes.csv"):
        yield {
            "routeId": row["routeId"],
            "source": "trip.ferizy.com",
            "originHarbourId": row["originHarbourId"],
            "destinationHarbourId": "",
            "originHarbourName": row["originHarbourName"],
            "originProvince": row["originProvince"],
            "origin": row["origin"],
            "destination": row["destination"],
            "destinationProvince": row["destinationProvince"],
            "shipClassId": "",
            "shipClass": "",
        }


def classic_rows():
    for row in read(EXPORTS / "ferizy-classic" / "ferizy_classic_routes.csv"):
        origin_id = row["origin_id"]
        destination_id = row["destination_id"]
        ship_id = row["ship_class_id"]
        origin_name, _, origin_province = row["origin"].partition(", ")
        destination_name, _, destination_province = row["destination"].partition(", ")
        yield {
            "routeId": f"classic-{origin_id}-{destination_id}-{ship_id}",
            "source": "ferizy.com",
            "originHarbourId": origin_id,
            "destinationHarbourId": destination_id,
            "originHarbourName": origin_name,
            "originProvince": origin_province or PORT_PROVINCES.get(origin_id, ""),
            "origin": origin_name,
            "destination": destination_name,
            "destinationProvince": destination_province or PORT_PROVINCES.get(destination_id, ""),
            "shipClassId": ship_id,
            "shipClass": row["ship_class"],
        }


rows = list(classic_rows()) + list(trip_rows())
rows.sort(key=lambda row: (row["source"], row["origin"], row["destination"], row["shipClassId"], row["routeId"]))
assert len(rows) == 146, len(rows)
assert len({row["routeId"] for row in rows}) == 146

output = EXPORTS / "ferizy_all_routes.csv"
with output.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerows(rows)
print(f"{output}: {len(rows)} routes + header")
print("sources:", {source: sum(row["source"] == source for row in rows) for source in sorted({row["source"] for row in rows})})
