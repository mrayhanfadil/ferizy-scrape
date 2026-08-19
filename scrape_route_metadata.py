#!/usr/bin/env python3
"""Collect public route-level service categories and check-in schedules."""
from __future__ import annotations

import json
import time
from pathlib import Path

from scrape_master import BASE, DATA, FerizyClient, body_data, record_response, wib_now, write_json

ROOT = Path('/home/fadil/trip-ferizy-scrape')
ROUTE_DIR = DATA / 'route_details'
ROUTE_DIR.mkdir(parents=True, exist_ok=True)


def load_routes() -> list[dict]:
    path = DATA / 'routes.json'
    if not path.exists():
        raise RuntimeError('routes.json is missing; run scrape_master.py first')
    return json.loads(path.read_text(encoding='utf-8'))


def main() -> None:
    routes = load_routes()
    client = FerizyClient()
    manifest = {
        'source': 'https://trip.ferizy.com/',
        'api_base': BASE,
        'scope': 'public route metadata only',
        'started_at_wib': wib_now(),
        'routes_requested': len(routes),
        'service_type_ok': 0,
        'checkin_ok': 0,
        'service_type_failures': [],
        'checkin_failures': [],
    }
    print('authenticated; routes', len(routes))
    for index, route in enumerate(routes, start=1):
        route_id = str(route.get('routeId', '')).strip()
        if not route_id:
            continue
        route_dir = ROUTE_DIR / route_id
        route_dir.mkdir(parents=True, exist_ok=True)
        write_json(route_dir / 'route.json', route)

        service_path = '/ferizy/homepage/service-type'
        service_file = route_dir / 'service_type.json'
        if service_file.exists():
            service_ok = True
        else:
            try:
                status, ctype, payload = client.request('GET', service_path, extra={'AIFRouteId': route_id}, max_attempts=3, timeout=30)
                record_response(service_file, status, ctype, payload, {
                    'method': 'GET', 'url': BASE + service_path,
                    'routeId': route_id, 'headers_extra': {'AIFRouteId': route_id},
                })
                service_ok = status == 200
                if service_ok:
                    manifest['service_type_ok'] += 1
                else:
                    manifest['service_type_failures'].append({'routeId': route_id, 'status': status})
            except Exception as exc:
                service_ok = False
                manifest['service_type_failures'].append({'routeId': route_id, 'error': repr(exc)})
            time.sleep(1)

        checkin_path = '/ferizy/ticket/schedule/check_in'
        checkin_file = route_dir / 'checkin.json'
        if checkin_file.exists():
            checkin_ok = True
        else:
            try:
                from scrape_master import timestamp
                device_time = timestamp()
                status, ctype, payload = client.request('GET', checkin_path, extra={
                    'AIFRouteId': route_id,
                    'AIFDeviceTime': device_time,
                }, max_attempts=3, timeout=30)
                record_response(checkin_file, status, ctype, payload, {
                    'method': 'GET', 'url': BASE + checkin_path,
                    'routeId': route_id,
                    'headers_extra': {'AIFRouteId': route_id, 'AIFDeviceTime': device_time},
                })
                checkin_ok = status == 200
                if checkin_ok:
                    manifest['checkin_ok'] += 1
                else:
                    manifest['checkin_failures'].append({'routeId': route_id, 'status': status})
            except Exception as exc:
                checkin_ok = False
                manifest['checkin_failures'].append({'routeId': route_id, 'error': repr(exc)})
            time.sleep(1)

        print(f'route {index}/{len(routes)} id={route_id} service={service_ok} checkin={checkin_ok}')

        if index % 10 == 0:
            manifest['checkpoint_at_wib'] = wib_now()
            write_json(ROOT / 'route_metadata_manifest.json', manifest)

    manifest['finished_at_wib'] = wib_now()
    write_json(ROOT / 'route_metadata_manifest.json', manifest)
    print(json.dumps({
        'routes': len(routes),
        'service_type_ok': manifest['service_type_ok'],
        'checkin_ok': manifest['checkin_ok'],
        'service_type_failures': len(manifest['service_type_failures']),
        'checkin_failures': len(manifest['checkin_failures']),
    }))


if __name__ == '__main__':
    main()
