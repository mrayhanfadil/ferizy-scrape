#!/usr/bin/env python3
"""Run the trip fare snapshot scraper over an inclusive date range.

Each date is isolated by the underlying scraper's date-specific raw/cache and
CSV paths. Completed dates are safe to rerun because the underlying scraper
reuses checkpointed envelopes unless --force is passed to it.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRAPER = ROOT / "scripts" / "scrape_fares_trip_fullscale.py"
EXPORTS = ROOT / "exports"


def dates_between(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def main() -> int:
    parser = argparse.ArgumentParser(description="Trip Ferizy fare snapshot date-range runner")
    parser.add_argument("--start-date", required=True, help="Inclusive YYYY-MM-DD")
    parser.add_argument("--end-date", required=True, help="Inclusive YYYY-MM-DD")
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
            sys.executable,
            str(SCRAPER),
            "--date",
            target_text,
            "--workers",
            str(max(1, min(args.workers, 8))),
        ]
        completed = subprocess.run(command, cwd=ROOT, check=False)
        elapsed = round(time.time() - started, 2)
        daily_manifest = EXPORTS / f"trip_fares_manifest_{target_text}.json"
        summary = {
            "date": target_text,
            "returncode": completed.returncode,
            "elapsed_seconds": elapsed,
            "manifest": str(daily_manifest.relative_to(ROOT)),
        }
        if daily_manifest.exists():
            try:
                summary["daily"] = json.loads(daily_manifest.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                summary["daily_manifest_error"] = "invalid_json"
        results.append(summary)
        print(json.dumps(summary, ensure_ascii=False), flush=True)

    range_manifest = {
        "source": "https://trip.ferizy.com/",
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "dates_requested": len(results),
        "dates_completed": sum(item["returncode"] == 0 for item in results),
        "dates": results,
    }
    output = EXPORTS / f"trip_fares_snapshot_{start.isoformat()}_{end.isoformat()}.json"
    output.write_text(json.dumps(range_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"=== RANGE COMPLETE: {output} ===", flush=True)
    return 0 if range_manifest["dates_completed"] == range_manifest["dates_requested"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
