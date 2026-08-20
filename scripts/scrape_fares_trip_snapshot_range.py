#!/usr/bin/env python3
"""Run and aggregate trip.ferizy.com fare snapshots over an inclusive date range."""
from __future__ import annotations

import argparse
import collections
import csv
import json
import subprocess
import sys
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SCRAPER = ROOT / "scripts" / "scrape_fares_trip_fullscale.py"
EXPORTS = ROOT / "exports"

ALL_FIELDS = [
    "routeId", "originHarbourId", "origin", "destination", "destinationProvince",
    "serviceCategory", "serviceId", "serviceName", "vehicleClass", "departDate",
    "departTime", "scheduleId", "quota", "fareAmount", "totalPrice", "currency",
    "status", "statusCode", "message",
]
CLEAN_FIELDS = [field for field in ALL_FIELDS if field not in {"statusCode", "message"}]


def dates_between(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in fields} for row in rows)


def aggregate_union(start: date, end: date) -> dict[str, Any]:
    days = [target.isoformat() for target in dates_between(start, end)]
    rows: list[dict[str, Any]] = []
    for target in days:
        daily_path = EXPORTS / f"trip_fares_fullscale_all_{target}.csv"
        if not daily_path.exists():
            raise FileNotFoundError(f"missing daily matrix: {daily_path}")
        with daily_path.open(encoding="utf-8") as handle:
            rows.extend(csv.DictReader(handle))

    # One row per route/service/date. Prefer OK if a duplicate was produced.
    deduped: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for row in rows:
        key = (
            row.get("routeId", ""),
            row.get("serviceCategory", ""),
            row.get("serviceId", ""),
            row.get("departDate", ""),
        )
        previous = deduped.get(key)
        if previous is None or (previous.get("status") != "OK" and row.get("status") == "OK"):
            deduped[key] = row

    rows = sorted(
        deduped.values(),
        key=lambda row: (
            row.get("routeId", ""), row.get("departDate", ""),
            row.get("serviceCategory", ""), row.get("serviceId", ""),
        ),
    )
    clean_rows = [row for row in rows if row.get("status") == "OK"]

    start_text = start.isoformat()
    end_text = end.isoformat()
    clean_path = EXPORTS / f"trip_fares_snapshot_{start_text}_{end_text}.csv"
    matrix_path = EXPORTS / f"trip_fares_snapshot_matrix_{start_text}_{end_text}.csv"
    missing_path = EXPORTS / f"trip_fares_snapshot_missing_routes_{start_text}_{end_text}.json"
    write_csv(clean_path, CLEAN_FIELDS, clean_rows)
    write_csv(matrix_path, ALL_FIELDS, rows)

    route_ids = {
        str(route["routeId"])
        for route in json.loads((DATA / "routes.json").read_text(encoding="utf-8"))
    }
    route_service_keys = {
        (row.get("routeId", ""), row.get("serviceCategory", ""), row.get("serviceId", ""))
        for row in rows
    }
    ok_route_service_keys = {
        (row.get("routeId", ""), row.get("serviceCategory", ""), row.get("serviceId", ""))
        for row in clean_rows
    }
    vehicle_keys = {key for key in route_service_keys if key[1] == "Kendaraan"}
    ok_vehicle_keys = {key for key in ok_route_service_keys if key[1] == "Kendaraan"}
    ok_routes = {row.get("routeId", "") for row in clean_rows}
    missing_routes = sorted(route_ids - ok_routes)
    missing_path.write_text(
        json.dumps(
            {"start_date": start_text, "end_date": end_text, "routes_without_ok": missing_routes},
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    union = {
        "start_date": start_text,
        "end_date": end_text,
        "dates": days,
        "dates_completed": len(days),
        "routes_expected": len(route_ids),
        "routes_present": len({row.get("routeId", "") for row in rows}),
        "routes_with_any_ok": len(ok_routes),
        "routes_without_ok": len(missing_routes),
        "route_service_keys": len(route_service_keys),
        "route_service_keys_with_any_ok": len(ok_route_service_keys),
        "vehicle_service_keys": len(vehicle_keys),
        "vehicle_service_keys_with_any_ok": len(ok_vehicle_keys),
        "live_fare_rows": len(clean_rows),
        "matrix_rows": len(rows),
        "status_counts": dict(collections.Counter(row.get("status", "") for row in rows)),
        "clean_export": str(clean_path.relative_to(ROOT)),
        "matrix_export": str(matrix_path.relative_to(ROOT)),
        "missing_routes_export": str(missing_path.relative_to(ROOT)),
    }
    return union


def main() -> int:
    parser = argparse.ArgumentParser(description="Trip Ferizy fare snapshot date-range runner")
    parser.add_argument("--start-date", "--start", dest="start_date", required=True, help="Inclusive YYYY-MM-DD")
    parser.add_argument("--end-date", "--end", dest="end_date", required=True, help="Inclusive YYYY-MM-DD")
    parser.add_argument("--workers", type=int, default=4, help="Workers passed to daily scraper")
    args = parser.parse_args()

    start = date.fromisoformat(args.start_date)
    end = date.fromisoformat(args.end_date)
    if end < start:
        raise SystemExit("end date must be on or after start date")

    results = []
    for target in dates_between(start, end):
        target_text = target.isoformat()
        started = time.time()
        print(f"=== RANGE DATE {target_text} ===", flush=True)
        command = [
            sys.executable, str(SCRAPER), "--date", target_text,
            "--workers", str(max(1, min(args.workers, 8))),
        ]
        completed = subprocess.run(command, cwd=ROOT, check=False)
        daily_manifest = EXPORTS / f"trip_fares_manifest_{target_text}.json"
        summary: dict[str, Any] = {
            "date": target_text,
            "returncode": completed.returncode,
            "elapsed_seconds": round(time.time() - started, 2),
            "manifest": str(daily_manifest.relative_to(ROOT)),
        }
        if daily_manifest.exists():
            try:
                summary["daily"] = json.loads(daily_manifest.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                summary["daily_manifest_error"] = "invalid_json"
        results.append(summary)
        print(json.dumps(summary, ensure_ascii=False), flush=True)

    union = aggregate_union(start, end)
    range_manifest = {
        "source": "https://trip.ferizy.com/",
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "dates_requested": len(results),
        "dates_completed": sum(item["returncode"] == 0 for item in results),
        "dates": results,
        "union": union,
    }
    output = EXPORTS / f"trip_fares_snapshot_{start.isoformat()}_{end.isoformat()}.json"
    output.write_text(json.dumps(range_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"union": union}, ensure_ascii=False, indent=2), flush=True)
    print(f"=== RANGE COMPLETE: {output} ===", flush=True)
    return 0 if range_manifest["dates_completed"] == range_manifest["dates_requested"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
