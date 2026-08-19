#!/usr/bin/env python3
"""Collect route service/check-in metadata with two bounded parallel requests."""
from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from scrape_master import BASE, DATA, FerizyClient, record_response, timestamp, wib_now, write_json

ROOT = Path('/home/fadil/trip-ferizy-scrape')
ROUTE_DIR = DATA / 'route_details'


def load_routes() -> list[dict]:
    path = DATA / 'routes.json'
    if not path.exists():
        raise RuntimeError('routes.json is missing; run scrape_master.py first')
    return json.loads(path.read_text(encoding='utf-8'))


def fetch_service(client: FerizyClient, route: dict, out: Path) -> tuple[bool, dict | None]:
    route_id = str(route['routeId']).strip()
    path = '/ferizy/homepage/service-type'
    target = out / 'service_type.json'
    if target.exists():
        return True, None
    try:
        status, ctype, payload = client.request('GET', path, extra={'AIFRouteId': route_id}, max_attempts=3, timeout=30)
        record_response(target, status, ctype, payload, {
            'method': 'GET', 'url': BASE + path, 'routeId': route_id,
            'headers_extra': {'AIFRouteId': route_id},
        })
        return status == 200, None if status == 200 else {'routeId': route_id, 'status': status}
    except Exception as exc:
        return False, {'routeId': route_id, 'error': repr(exc)}


def fetch_checkin(client: FerizyClient, route: dict, out: Path) -> tuple[bool, dict | None]:
    route_id = str(route['routeId']).strip()
    path = '/ferizy/ticket/schedule/check_in'
    target = out / 'checkin.json'
    if target.exists():
        return True, None
    try:
        device_time = timestamp()
        status, ctype, payload = client.request('GET', path, extra={
            'AIFRouteId': route_id,
            'AIFDeviceTime': device_time,
        }, max_attempts=3, timeout=30)
        record_response(target, status, ctype, payload, {
            'method': 'GET', 'url': BASE + path, 'routeId': route_id,
            'headers_extra': {'AIFRouteId': route_id, 'AIFDeviceTime': device_time},
        })
        return status == 200, None if status == 200 else {'routeId': route_id, 'status': status}
    except Exception as exc:
        return False, {'routeId': route_id, 'error': repr(exc)}


def main() -> None:
    routes = load_routes()
    service_client = FerizyClient()
    checkin_client = FerizyClient()
    manifest_path = ROOT / 'route_metadata_manifest.json'
    manifest = {
        'source': 'https://trip.ferizy.com/', 'api_base': BASE,
        'scope': 'public route metadata only', 'started_at_wib': wib_now(),
        'routes_requested': len(routes), 'service_type_ok': 0, 'checkin_ok': 0,
        'service_type_failures': [], 'checkin_failures': [],
    }
    print('authenticated; routes', len(routes), flush=True)
    for index, route in enumerate(routes, start=1):
        route_id = str(route.get('routeId', '')).strip()
        if not route_id:
            continue
        route_dir = ROUTE_DIR / route_id
        route_dir.mkdir(parents=True, exist_ok=True)
        write_json(route_dir / 'route.json', route)
        with ThreadPoolExecutor(max_workers=2) as pool:
            service_future = pool.submit(fetch_service, service_client, route, route_dir)
            checkin_future = pool.submit(fetch_checkin, checkin_client, route, route_dir)
            service_ok, service_error = service_future.result()
            checkin_ok, checkin_error = checkin_future.result()
        if service_ok:
            manifest['service_type_ok'] += 1
        elif service_error:
            manifest['service_type_failures'].append(service_error)
        if checkin_ok:
            manifest['checkin_ok'] += 1
        elif checkin_error:
            manifest['checkin_failures'].append(checkin_error)
        print(f'route {index}/{len(routes)} id={route_id} service={service_ok} checkin={checkin_ok}', flush=True)
        if index % 10 == 0:
            manifest['checkpoint_at_wib'] = wib_now()
            write_json(manifest_path, manifest)
        time.sleep(0.5)
    manifest['finished_at_wib'] = wib_now()
    write_json(manifest_path, manifest)
    print(json.dumps({
        'routes': len(routes), 'service_type_ok': manifest['service_type_ok'],
        'checkin_ok': manifest['checkin_ok'],
        'service_type_failures': len(manifest['service_type_failures']),
        'checkin_failures': len(manifest['checkin_failures']),
    }), flush=True)


if __name__ == '__main__':
    main()
