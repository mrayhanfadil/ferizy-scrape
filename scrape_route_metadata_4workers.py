#!/usr/bin/env python3
"""Resume route metadata collection with four isolated API clients."""
from __future__ import annotations

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from scrape_master import BASE, DATA, FerizyClient, record_response, timestamp, wib_now, write_json

ROOT = Path('/home/fadil/trip-ferizy-scrape')
ROUTE_DIR = DATA / 'route_details'
PRINT_LOCK = threading.Lock()


def load_routes() -> list[dict]:
    return json.loads((DATA / 'routes.json').read_text(encoding='utf-8'))


def existing_status(path: Path) -> bool | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding='utf-8')).get('status') == 200
    except Exception:
        return False


def fetch_route(client: FerizyClient, route: dict) -> dict:
    route_id = str(route['routeId']).strip()
    out = ROUTE_DIR / route_id
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / 'route.json', route)
    result = {'routeId': route_id, 'service': None, 'checkin': None, 'errors': []}

    service_file = out / 'service_type.json'
    old = existing_status(service_file)
    if old is not None:
        result['service'] = old
    else:
        path = '/ferizy/homepage/service-type'
        try:
            status, ctype, payload = client.request('GET', path, extra={'AIFRouteId': route_id}, max_attempts=3, timeout=30)
            record_response(service_file, status, ctype, payload, {
                'method': 'GET', 'url': BASE + path, 'routeId': route_id,
                'headers_extra': {'AIFRouteId': route_id},
            })
            result['service'] = status == 200
        except Exception as exc:
            result['service'] = False
            result['errors'].append({'kind': 'service', 'error': repr(exc)})

    checkin_file = out / 'checkin.json'
    old = existing_status(checkin_file)
    if old is not None:
        result['checkin'] = old
    else:
        path = '/ferizy/ticket/schedule/check_in'
        try:
            device_time = timestamp()
            status, ctype, payload = client.request('GET', path, extra={
                'AIFRouteId': route_id, 'AIFDeviceTime': device_time,
            }, max_attempts=3, timeout=30)
            record_response(checkin_file, status, ctype, payload, {
                'method': 'GET', 'url': BASE + path, 'routeId': route_id,
                'headers_extra': {'AIFRouteId': route_id, 'AIFDeviceTime': device_time},
            })
            result['checkin'] = status == 200
        except Exception as exc:
            result['checkin'] = False
            result['errors'].append({'kind': 'checkin', 'error': repr(exc)})
    return result


def worker(worker_id: int, routes: list[dict], client: FerizyClient) -> list[dict]:
    results = []
    for route in routes:
        result = fetch_route(client, route)
        result['worker'] = worker_id
        results.append(result)
        with PRINT_LOCK:
            print(f"worker={worker_id} route={result['routeId']} service={result['service']} checkin={result['checkin']}", flush=True)
        time.sleep(0.25)
    return results


def main() -> None:
    routes = load_routes()
    # Four separate sessions avoid sharing requests.Session across threads.
    clients = [FerizyClient() for _ in range(4)]
    chunks = [routes[i::4] for i in range(4)]
    print('authenticated clients=4 routes=', len(routes), flush=True)
    started = wib_now()
    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(worker, i, chunks[i], clients[i]) for i in range(4)]
        for future in futures:
            results.extend(future.result())

    results.sort(key=lambda item: item['routeId'])
    errors = [error for item in results for error in item['errors']]
    manifest = {
        'source': 'https://trip.ferizy.com/', 'api_base': BASE,
        'scope': 'public route metadata only', 'started_at_wib': started,
        'finished_at_wib': wib_now(), 'routes_requested': len(routes),
        'service_type_ok': sum(item['service'] is True for item in results),
        'checkin_ok': sum(item['checkin'] is True for item in results),
        'service_type_failures': [item for item in results if item['service'] is False],
        'checkin_failures': [item for item in results if item['checkin'] is False],
        'transport_errors': errors,
    }
    write_json(ROOT / 'route_metadata_manifest.json', manifest)
    write_json(ROOT / 'route_metadata_results.json', results)
    print(json.dumps({
        'routes': len(routes),
        'service_type_ok': manifest['service_type_ok'],
        'checkin_ok': manifest['checkin_ok'],
        'service_type_failures': len(manifest['service_type_failures']),
        'checkin_failures': len(manifest['checkin_failures']),
        'transport_errors': len(errors),
    }), flush=True)


if __name__ == '__main__':
    main()
