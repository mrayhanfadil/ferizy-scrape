#!/usr/bin/env python3
"""Collect public Ferizy portal master data and route directories.

This deliberately excludes authenticated account/order/payment operations.
It checkpoints each response so interruptions do not lose completed work.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import subprocess
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import requests

ROOT = Path('/home/fadil/trip-ferizy-scrape')
DATA = ROOT / 'data'
DEST = DATA / 'destinations'
DEST.mkdir(parents=True, exist_ok=True)
BASE = 'https://api-gateway-1.ferizy.com'
PORTAL = 'https://trip.ferizy.com'
CLIENT_ID = 'asdp@ticket-prod.com'
KEY = base64.b64decode('YWQxYzQ5OGU5MjE0NDJjZg==')


def wib_now() -> str:
    return datetime.now(timezone(timedelta(hours=7))).isoformat()


def aes(value: str, decrypt: bool = False) -> str:
    command = ['openssl', 'enc']
    if decrypt:
        command.append('-d')
    command += ['-aes-128-ecb', '-K', KEY.hex(), '-a', '-A']
    result = subprocess.run(command, input=value.encode(), capture_output=True, check=True)
    return result.stdout.decode().strip()


def timestamp() -> str:
    return datetime.now(timezone(timedelta(hours=7))).strftime('%Y-%m-%dT%H:%M:%S') + '+07:00'


class FerizyClient:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36',
            'Origin': PORTAL,
            'Referer': PORTAL + '/',
            'Connection': 'close',
        })
        self.token = ''
        self.secret = ''
        self.authenticate()

    def authenticate(self) -> None:
        stamp = timestamp()
        response = self.session.post(
            BASE + '/ferizy/auth/VG9rZW4=',
            headers={
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'X-ClientId': aes(CLIENT_ID),
                'X-Signature': aes(CLIENT_ID + '|' + stamp),
                'X-Timestamp': stamp,
            },
            json={'grant_type': 'client_credentials'},
            timeout=30,
        )
        response.raise_for_status()
        data = (response.json().get('data') or {})
        self.token = data['accessToken']
        self.secret = aes(data['clientSecret'], decrypt=True)

    def request(self, method: str, path: str, body: str = '', extra: dict[str, str] | None = None, max_attempts: int = 5, timeout: int = 90) -> tuple[int, str, Any]:
        last_error: Exception | None = None
        for attempt in range(1, max_attempts + 1):
            try:
                stamp = timestamp()
                signature_input = f'{method}:{path}:{self.token}:{hashlib.sha256(body.encode()).hexdigest()}:{stamp}'
                signature = hmac.new(self.secret.encode(), signature_input.encode(), hashlib.sha512).hexdigest()
                headers = {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer ' + self.token,
                    'AIFSignature': signature,
                    'AIFMethod': method,
                    'AIFClientId': CLIENT_ID,
                    'AIFTimestamp': stamp,
                    'AIFUrlPath': path,
                }
                if extra:
                    headers.update(extra)
                response = self.session.request(
                    method,
                    BASE + path,
                    headers=headers,
                    data=body if body else None,
                    timeout=timeout,
                )
                content_type = response.headers.get('content-type', '')
                try:
                    payload = response.json() if 'json' in content_type else response.text
                except Exception:
                    payload = response.text
                if response.status_code in (401, 403):
                    self.authenticate()
                    raise RuntimeError(f'auth status {response.status_code}')
                if response.status_code >= 500:
                    raise RuntimeError(f'server status {response.status_code}')
                return response.status_code, content_type, payload
            except Exception as exc:
                last_error = exc
                if attempt < max_attempts:
                    time.sleep(min(2 * attempt, 10))
        raise RuntimeError(f'{method} {path} failed after retries: {last_error}')


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def record_response(path: Path, status: int, content_type: str, payload: Any, request: dict[str, Any]) -> None:
    write_json(path, {
        'request': request,
        'status': status,
        'content_type': content_type,
        'retrieved_at_wib': wib_now(),
        'body': payload,
    })


def body_data(payload: Any, container: str) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    node = payload.get(container) or {}
    if not isinstance(node, dict):
        return []
    data = node.get('data')
    return data if isinstance(data, list) else []


def main() -> None:
    started = wib_now()
    client = FerizyClient()
    print('authenticated')

    # Fetch the portal's public homepage/master endpoints.
    public_specs = [
        ('homepage_origin', '/ferizy/homepage/origin', {}),
        ('homepage_country', '/ferizy/homepage/country', {}),
        ('account_regency', '/ferizy/account/regency', {}),
        ('ticket_service', '/ferizy/ticket/service', {}),
        ('homepage_carrousel', '/ferizy/homepage/carousell', {}),
        ('homepage_maintenance', '/ferizy/homepage/maintenance', {}),
        ('parameter_bulk_identity', '/ferizy/homepage/parameter/bulk', {'AIFBulkParameterName': '%max_identity_type%'}),
    ]
    responses: dict[str, Any] = {}
    for name, path, extra in public_specs:
        status, content_type, payload = client.request('GET', path, extra=extra)
        record_response(DATA / f'{name}.json', status, content_type, payload, {
            'method': 'GET', 'url': BASE + path, 'headers_extra': extra,
        })
        responses[name] = payload
        print(name, status)
        time.sleep(1)

    origins = body_data(responses['homepage_origin'], 'originHarbour')
    if not origins:
        raise RuntimeError('origin directory was empty; refusing to continue')

    routes: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for index, origin in enumerate(origins, start=1):
        origin_id = str(origin.get('harbourId', '')).strip()
        if not origin_id:
            failures.append({'origin': origin, 'reason': 'missing harbourId'})
            continue
        path = '/ferizy/homepage/destination'
        try:
            status, content_type, payload = client.request('GET', path, extra={'AIFHarbourOriginId': origin_id})
            record_response(DEST / f'{origin_id}.json', status, content_type, payload, {
                'method': 'GET', 'url': BASE + path, 'origin': origin,
                'headers_extra': {'AIFHarbourOriginId': origin_id},
            })
            destinations = body_data(payload, 'destinationHarbour')
            for destination in destinations:
                routes.append({
                    'originHarbourId': origin_id,
                    'originHarbourName': origin.get('harbourName'),
                    'originProvince': origin.get('province'),
                    **destination,
                })
            print(f'destination {index}/{len(origins)} origin={origin_id} status={status} routes={len(destinations)}')
        except Exception as exc:
            failures.append({'origin': origin, 'reason': repr(exc)})
            print(f'destination {index}/{len(origins)} origin={origin_id} FAILED')
        time.sleep(1)

    # Stable route identity: routeId can appear in more than one directory response.
    unique: dict[str, dict[str, Any]] = {}
    duplicates = 0
    for route in routes:
        route_id = str(route.get('routeId', '')).strip()
        if not route_id:
            continue
        if route_id in unique:
            duplicates += 1
            continue
        unique[route_id] = route
    route_list = sorted(unique.values(), key=lambda item: (item.get('originHarbourName') or '', item.get('destination') or '', str(item.get('routeId'))))
    write_json(DATA / 'routes.json', route_list)
    write_json(DATA / 'crawl_failures.json', failures)
    write_json(ROOT / 'crawl_manifest.json', {
        'source': PORTAL + '/',
        'api_base': BASE,
        'scope': 'public portal/master data only; no authenticated account/order/payment data',
        'started_at_wib': started,
        'finished_at_wib': wib_now(),
        'origins': len(origins),
        'origin_responses': len(origins) - len(failures),
        'route_records_raw': len(routes),
        'unique_routes': len(route_list),
        'duplicate_route_records': duplicates,
        'failed_origins': len(failures),
        'files': {
            'homepage_master': [name + '.json' for name, _, _ in public_specs],
            'per_origin_destinations': 'data/destinations/<harbourId>.json',
            'normalized_routes': 'data/routes.json',
            'failures': 'data/crawl_failures.json',
        },
    })
    print('SUMMARY', json.dumps({
        'origins': len(origins), 'routes_raw': len(routes), 'unique_routes': len(route_list),
        'duplicates': duplicates, 'failures': len(failures),
    }))


if __name__ == '__main__':
    main()
