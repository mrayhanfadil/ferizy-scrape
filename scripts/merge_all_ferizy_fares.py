#!/usr/bin/env python3
"""Merge Trip and Classic Ferizy fare snapshots into one normalized CSV."""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPORTS = ROOT / "exports"

FIELDS = [
    "source", "routeId", "originHarbourId", "destinationHarbourId",
    "origin", "destination", "destinationProvince", "shipClass",
    "serviceCategory", "serviceId", "serviceName", "vehicleClass",
    "departDate", "departTime", "scheduleId", "quota", "fareAmount",
    "totalPrice", "currency", "status", "statusCode", "message", "sourceFile",
]

PORT_IDS = {
    "Bakauheni": "3", "Merak": "2", "Gilimanuk": "4", "Ketapang": "5",
}
PORT_NAMES = {value: key for key, value in PORT_IDS.items()}


def blank_row() -> dict[str, str]:
    return {field: "" for field in FIELDS}


def map_trip(row: dict[str, str]) -> dict[str, str]:
    result = blank_row()
    result.update({
        "source": "trip.ferizy.com",
        "routeId": row.get("routeId", ""),
        "originHarbourId": row.get("originHarbourId", ""),
        "origin": row.get("origin", ""),
        "destination": row.get("destination", ""),
        "destinationProvince": row.get("destinationProvince", ""),
        "serviceCategory": row.get("serviceCategory", ""),
        "serviceId": row.get("serviceId", ""),
        "serviceName": row.get("serviceName", ""),
        "vehicleClass": row.get("vehicleClass", ""),
        "departDate": row.get("departDate", ""),
        "departTime": row.get("departTime", ""),
        "scheduleId": row.get("scheduleId", ""),
        "quota": row.get("quota", ""),
        "fareAmount": row.get("fareAmount", ""),
        "totalPrice": row.get("totalPrice", ""),
        "currency": row.get("currency", "IDR"),
        "status": row.get("status", ""),
        "statusCode": row.get("statusCode", "200") or "200",
        "message": row.get("message", ""),
        "sourceFile": row.get("sourceFile", ""),
    })
    return result


def classic_ids(source_file: str) -> tuple[str, str, str, str]:
    match = re.search(r"fare_(\d+)_(\d+)_(\d+)_vc(\d+)_", source_file)
    if not match:
        raise ValueError(f"cannot parse classic sourceFile: {source_file}")
    origin_id, destination_id, ship_id, vehicle_id = match.groups()
    return origin_id, destination_id, ship_id, vehicle_id


def map_classic_clean(row: dict[str, str]) -> dict[str, str]:
    source_file = row.get("sourceFile", "")
    origin_id, destination_id, ship_id, vehicle_id = classic_ids(source_file)
    result = blank_row()
    result.update({
        "source": "ferizy.com",
        "routeId": f"classic-{origin_id}-{destination_id}-sc{ship_id}",
        "originHarbourId": origin_id,
        "destinationHarbourId": destination_id,
        "origin": row.get("origin", PORT_NAMES.get(origin_id, "")),
        "destination": row.get("destination", PORT_NAMES.get(destination_id, "")),
        "shipClass": row.get("shipClass", ""),
        "serviceCategory": "Kendaraan",
        "serviceId": vehicle_id,
        "serviceName": row.get("vehicleClass", ""),
        "vehicleClass": row.get("vehicleClass", ""),
        "departDate": row.get("departDate", ""),
        "departTime": row.get("departTime", ""),
        "quota": row.get("kuota", ""),
        "fareAmount": row.get("fareAmount", ""),
        "totalPrice": row.get("totalFare", row.get("fareAmount", "")),
        "currency": row.get("currency", "IDR"),
        "status": "OK",
        "statusCode": "200",
        "sourceFile": source_file,
    })
    return result


def map_classic_matrix(row: dict[str, str]) -> dict[str, str]:
    origin_id, destination_id = [part.strip() for part in row.get("route", " → ").split("→", 1)]
    ship_id = row.get("ship_class", "").replace("SC", "")
    vehicle_id = row.get("vehicle_class", "").replace("VC", "")
    service = row.get("service", "")
    category = "Pejalan Kaki" if "Pejalan" in service else "Kendaraan"
    status = row.get("status", "")
    result = blank_row()
    result.update({
        "source": "ferizy.com",
        "routeId": f"classic-{origin_id}-{destination_id}-sc{ship_id}",
        "originHarbourId": origin_id,
        "destinationHarbourId": destination_id,
        "origin": PORT_NAMES.get(origin_id, ""),
        "destination": PORT_NAMES.get(destination_id, ""),
        "shipClass": f"SC{ship_id}",
        "serviceCategory": category,
        "serviceId": vehicle_id,
        "serviceName": row.get("vehicle_class_name", ""),
        "vehicleClass": row.get("vehicle_class_name", ""),
        "departDate": row.get("depart_date", ""),
        "departTime": row.get("depart_time", ""),
        "quota": row.get("sample_quota", "") or row.get("available_quota", ""),
        "fareAmount": row.get("sample_total", ""),
        "totalPrice": row.get("sample_total", ""),
        "currency": row.get("currency", "IDR"),
        "status": status,
        "statusCode": "200" if status == "OK" else "0",
        "message": "",
        "sourceFile": "unified_fares_ferizy_classic_all_2026-08-20.csv",
    })
    return result


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge all Ferizy fare snapshots")
    parser.add_argument("--start-date", default="2026-08-20")
    parser.add_argument("--end-date", default="2026-08-26")
    args = parser.parse_args()

    period_clean = EXPORTS / f"trip_fares_snapshot_{args.start_date}_{args.end_date}.csv"
    period_matrix = EXPORTS / f"trip_fares_snapshot_matrix_{args.start_date}_{args.end_date}.csv"
    classic_clean = EXPORTS / "unified_fares_ferizy_classic.csv"
    classic_matrix = EXPORTS / "unified_fares_ferizy_classic_all_2026-08-20.csv"

    clean_rows = [map_trip(row) for row in read_rows(period_clean)]
    clean_rows.extend(map_classic_clean(row) for row in read_rows(classic_clean))
    clean_rows.sort(key=lambda row: (row["source"], row["routeId"], row["departDate"], row["serviceId"]))

    matrix_rows = [map_trip(row) for row in read_rows(period_matrix)]
    matrix_rows.extend(map_classic_matrix(row) for row in read_rows(classic_matrix))
    matrix_rows.sort(key=lambda row: (row["source"], row["routeId"], row["departDate"], row["serviceId"]))

    clean_path = EXPORTS / f"ferizy_all_fares_{args.start_date}_{args.end_date}.csv"
    matrix_path = EXPORTS / f"ferizy_all_fares_matrix_{args.start_date}_{args.end_date}.csv"
    write_rows(clean_path, clean_rows)
    write_rows(matrix_path, matrix_rows)

    manifest = {
        "start_date": args.start_date,
        "end_date": args.end_date,
        "clean_rows": len(clean_rows),
        "clean_trip_rows": sum(row["source"] == "trip.ferizy.com" for row in clean_rows),
        "clean_classic_rows": sum(row["source"] == "ferizy.com" for row in clean_rows),
        "matrix_rows": len(matrix_rows),
        "matrix_trip_rows": sum(row["source"] == "trip.ferizy.com" for row in matrix_rows),
        "matrix_classic_rows": sum(row["source"] == "ferizy.com" for row in matrix_rows),
        "schema": FIELDS,
        "clean_export": str(clean_path.relative_to(ROOT)),
        "matrix_export": str(matrix_path.relative_to(ROOT)),
        "note": "Single normalized CSV across Trip and Classic portals; source is retained only for provenance.",
    }
    manifest_path = EXPORTS / f"ferizy_all_fares_manifest_{args.start_date}_{args.end_date}.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
