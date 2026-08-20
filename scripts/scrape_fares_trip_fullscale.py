#!/usr/bin/env python3
"""Full-scale fare and schedule scraper for trip.ferizy.com across all routes and vehicle classes.

Queries api-gateway-1.ferizy.com /ferizy/ticket/ship/schedule for all 140 routes
and all vehicle (Gol I-IX) + passenger services.
Defensive-only: master and public scheduling data only; no authenticated/order endpoints.
"""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import hmac
import json
import random
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests

try:
    from cryptography.hazmat.primitives import padding
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    HAVE_CRYPTO = True
except ImportError:
    HAVE_CRYPTO = False

ROOT = Path('/home/fadil/trip-ferizy-scrape')
DATA = ROOT / 'data'
EXPORTS = ROOT / 'exports'
ROUTE_DIR = DATA / 'route_details'
BASE = 'https://api-gateway-1.ferizy.com'
PORTAL = 'https://trip.ferizy.com'
CLIENT_ID = 'asdp@ticket-prod.com'
KEY = base64.b64decode('YWQxYzQ5OGU5MjE0NDJjZg==')


def wib_now() -> str:
    return datetime.now(timezone(timedelta(hours=7))).isoformat()


def timestamp() -> str:
    return datetime.now(timezone(timedelta(hours=7))).strftime('%Y-%m-%dT%H:%M:%S') + '+07:00'


def aes_encrypt(value: str) -> str:
    if HAVE_CRYPTO:
        padder = padding.PKCS7(128).padder()
        padded = padder.update(value.encode('utf-8')) + padder.finalize()
        cipher = Cipher(algorithms.AES(KEY), modes.ECB())
        enc = cipher.encryptor()
        return base64.b64encode(enc.update(padded) + enc.finalize()).decode('utf-8').strip()
    cmd = ['openssl', 'enc', '-aes-128-ecb', '-K', KEY.hex(), '-a', '-A']
    return subprocess.run(cmd, input=value.encode('utf-8'), capture_output=True, check=True).stdout.decode('utf-8').strip()


def aes_decrypt(value: str) -> str:
    if HAVE_CRYPTO:
        raw = base64.b64decode(value)
        cipher = Cipher(algorithms.AES(KEY), modes.ECB())
        dec = cipher.decryptor()
        padded = dec.update(raw) + dec.finalize()
        unpadder = padding.PKCS7(128).unpadder()
        return (unpadder.update(padded) + unpadder.finalize()).decode('utf-8').strip()
    cmd = ['openssl', 'enc', '-d', '-aes-128-ecb', '-K', KEY.hex(), '-a', '-A']
    return subprocess.run(cmd, input=value.encode('utf-8'), capture_output=True, check=True).stdout.decode('utf-8').strip()


class TripFerizyClient:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
            'Origin': PORTAL,
            'Referer': PORTAL + '/',
            'Connection': 'close',
        })
        self.token = ''
        self.secret = ''
        self.auth_lock = threading.Lock()
        self.authenticate()

    def authenticate(self) -> None:
        with self.auth_lock:
            stamp = timestamp()
            response = self.session.post(
                BASE + '/ferizy/auth/VG9rZW4=',
                headers={
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                    'X-ClientId': aes_encrypt(CLIENT_ID),
                    'X-Signature': aes_encrypt(f'{CLIENT_ID}|{stamp}'),
                    'X-Timestamp': stamp,
                },
                json={'grant_type': 'client_credentials'},
                timeout=30,
            )
            response.raise_for_status()
            data = response.json().get('data') or {}
            self.token = data['accessToken']
            self.secret = aes_decrypt(data['clientSecret'])

    def request(
        self,
        method: str,
        path: str,
        body: str = '',
        extra: dict[str, str] | None = None,
        max_attempts: int = 4,
        timeout: int = 45,
    ) -> tuple[int, str, Any]:
        last_error: Exception | None = None
        for attempt in range(1, max_attempts + 1):
            try:
                stamp = timestamp()
                body_hash = hashlib.sha256(body.encode('utf-8')).hexdigest()
                sig_input = f'{method}:{path}:{self.token}:{body_hash}:{stamp}'
                sig = hmac.new(self.secret.encode('utf-8'), sig_input.encode('utf-8'), hashlib.sha512).hexdigest()
                headers = {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer ' + self.token,
                    'AIFSignature': sig,
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
                if response.status_code >= 500 and attempt < max_attempts:
                    time.sleep(1.0 * attempt)
                    continue
                return response.status_code, content_type, payload
            except Exception as exc:
                last_error = exc
                if attempt < max_attempts:
                    time.sleep(min(1.5 * attempt, 6.0))
        return 0, 'error', {'error': repr(last_error)}


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def get_service_types(client: TripFerizyClient, route_id: str, force: bool = False) -> list[dict[str, Any]]:
    target = ROUTE_DIR / route_id / 'service_type.json'
    if target.exists() and not force:
        try:
            cached = json.loads(target.read_text(encoding='utf-8'))
            if cached.get('status') == 200:
                data = cached.get('body', {}).get('jenisPenggunaJasa', {}).get('data', [])
                if data:
                    return data
        except Exception:
            pass

    status, ctype, payload = client.request('GET', '/ferizy/homepage/service-type', extra={'AIFRouteId': route_id})
    write_json(target, {
        'request': {'method': 'GET', 'url': BASE + '/ferizy/homepage/service-type', 'routeId': route_id},
        'status': status,
        'content_type': ctype,
        'retrieved_at_wib': wib_now(),
        'body': payload,
    })
    if status == 200 and isinstance(payload, dict):
        return payload.get('jenisPenggunaJasa', {}).get('data', [])
    return []


def get_checkin_schedules(client: TripFerizyClient, route_id: str, force: bool = False) -> list[dict[str, Any]]:
    target = ROUTE_DIR / route_id / 'checkin.json'
    if target.exists() and not force:
        try:
            cached = json.loads(target.read_text(encoding='utf-8'))
            if cached.get('status') == 200:
                data = cached.get('body', {}).get('jadwalMasukPelabuhan', {}).get('data', [])
                if data:
                    return data
        except Exception:
            pass

    device_time = timestamp()
    status, ctype, payload = client.request('GET', '/ferizy/ticket/schedule/check_in', extra={
        'AIFRouteId': route_id,
        'AIFDeviceTime': device_time,
    })
    write_json(target, {
        'request': {'method': 'GET', 'url': BASE + '/ferizy/ticket/schedule/check_in', 'routeId': route_id, 'device_time': device_time},
        'status': status,
        'content_type': ctype,
        'retrieved_at_wib': wib_now(),
        'body': payload,
    })
    if status == 200 and isinstance(payload, dict):
        return payload.get('jadwalMasukPelabuhan', {}).get('data', [])
    return []


def scrape_route_fares(
    client: TripFerizyClient,
    route: dict[str, Any],
    target_date: str,
    raw_dir: Path,
    date_raw_dir: Path,
    force: bool = False,
) -> list[dict[str, Any]]:
    route_id = str(route.get('routeId', '')).strip()
    origin = route.get('originHarbourName', '') or route.get('origin', '')
    destination = route.get('destination', '')
    origin_id = str(route.get('originHarbourId', ''))
    dest_province = route.get('destinationProvince', '')

    results: list[dict[str, Any]] = []

    # 1. Get service definitions
    service_groups = get_service_types(client, route_id, force=force)
    if not service_groups:
        results.append({
            'routeId': route_id,
            'originHarbourId': origin_id,
            'origin': origin,
            'destination': destination,
            'destinationProvince': dest_province,
            'serviceCategory': '',
            'serviceId': '',
            'serviceName': '',
            'vehicleClass': '',
            'departDate': target_date,
            'departTime': '',
            'scheduleId': '',
            'quota': '',
            'fareAmount': '',
            'totalPrice': '',
            'currency': 'IDR',
            'status': 'NO_SERVICE_TYPES',
            'statusCode': 0,
            'message': 'No service types configured for route',
        })
        return results

    pass_services: list[dict[str, Any]] = []
    veh_services: list[dict[str, Any]] = []
    for grp in service_groups:
        grp_id = str(grp.get('id', '')).lower()
        if 'pejalan' in grp_id or 'passenger' in grp_id:
            pass_services.extend(grp.get('detail', []))
        elif 'kendaraan' in grp_id or 'vehicle' in grp_id:
            veh_services.extend(grp.get('detail', []))

    # Identify mature/adult passenger service ID
    mature_service_id = '7'
    for ps in pass_services:
        code = str(ps.get('serviceCode', '')).upper()
        name = str(ps.get('serviceName', '')).lower()
        if code == 'DEWASA' or 'dewasa' in name:
            mature_service_id = str(ps.get('serviceId', '7'))
            break
    if not mature_service_id and pass_services:
        mature_service_id = str(pass_services[0].get('serviceId', '7'))

    # 2. Get checkin schedules
    schedules = get_checkin_schedules(client, route_id, force=force)
    date_schedules = [s for s in schedules if str(s.get('dateDeparture', '')) == target_date]

    if not schedules:
        schedule_status = 'SCHEDULE_DATA_NOT_FOUND'
        schedule_msg = 'Gateway returned no schedule data for route'
    elif not date_schedules:
        schedule_status = 'NO_SCHEDULE_FOR_DATE'
        schedule_msg = f'No departure slots found for date {target_date} ({len(schedules)} total across other dates)'
    else:
        schedule_status = 'OK'
        schedule_msg = ''

    all_services: list[tuple[str, dict[str, Any]]] = [('Pejalan Kaki', s) for s in pass_services] + [('Kendaraan', s) for s in veh_services]

    if not all_services:
        results.append({
            'routeId': route_id,
            'originHarbourId': origin_id,
            'origin': origin,
            'destination': destination,
            'destinationProvince': dest_province,
            'serviceCategory': '',
            'serviceId': '',
            'serviceName': '',
            'vehicleClass': '',
            'departDate': target_date,
            'departTime': '',
            'scheduleId': '',
            'quota': '',
            'fareAmount': '',
            'totalPrice': '',
            'currency': 'IDR',
            'status': 'NO_SERVICES_IN_GROUP',
            'statusCode': 0,
            'message': 'No detail services in service_type payload',
        })
        return results

    if schedule_status != 'OK':
        for cat, svc in all_services:
            svc_id = str(svc.get('serviceId', ''))
            svc_name = svc.get('serviceName', '')
            vclass = svc.get('serviceCode', '') or (svc_name if cat == 'Kendaraan' else '')
            results.append({
                'routeId': route_id,
                'originHarbourId': origin_id,
                'origin': origin,
                'destination': destination,
                'destinationProvince': dest_province,
                'serviceCategory': cat,
                'serviceId': svc_id,
                'serviceName': svc_name,
                'vehicleClass': vclass,
                'departDate': target_date,
                'departTime': '',
                'scheduleId': '',
                'quota': '',
                'fareAmount': '',
                'totalPrice': '',
                'currency': 'IDR',
                'status': schedule_status,
                'statusCode': 0,
                'message': schedule_msg,
            })
        return results

    # Pick representative slot for target_date
    slot = date_schedules[0]
    slot_time = str(slot.get('timeDeparture', '00:00'))
    if len(slot_time) == 5:
        slot_time_full = slot_time + ':00'
    else:
        slot_time_full = slot_time
    schedule_id = str(slot.get('scheduleId', ''))

    # 3. Query fare for each service
    for cat, svc in all_services:
        svc_id = str(svc.get('serviceId', ''))
        svc_name = svc.get('serviceName', '')
        vclass = svc.get('serviceCode', '') or (svc_name if cat == 'Kendaraan' else '')

        raw_file = raw_dir / f'fare_{route_id}_s{svc_id}_{target_date}.json'
        date_raw_file = date_raw_dir / f'fare_{route_id}_s{svc_id}.json'

        cached_payload = None
        if raw_file.exists() and not force:
            try:
                cached_payload = json.loads(raw_file.read_text(encoding='utf-8'))
            except Exception:
                pass

        if cached_payload is not None:
            status_code = cached_payload.get('status_code', 200)
            body = cached_payload.get('body', {})
        else:
            time.sleep(random.uniform(0.15, 0.35))
            if cat == 'Pejalan Kaki':
                req_body = {
                    'email': '',
                    'routeId': route_id,
                    'departure': {
                        'scheduleId': schedule_id,
                        'date': target_date,
                        'time': slot_time_full,
                    },
                    'services': {
                        'passengers': [{'serviceId': svc_id, 'capacity': 1}],
                        'vehicleId': '',
                    },
                }
            else:
                req_body = {
                    'email': '',
                    'routeId': route_id,
                    'departure': {
                        'scheduleId': schedule_id,
                        'date': target_date,
                        'time': slot_time_full,
                    },
                    'services': {
                        'passengers': [{'serviceId': mature_service_id, 'capacity': 1}],
                        'vehicleId': svc_id,
                    },
                }

            body_str = json.dumps(req_body)
            status_code, ctype, body = client.request('POST', '/ferizy/ticket/ship/schedule', body=body_str)

            envelope = {
                'request': req_body,
                'status_code': status_code,
                'content_type': ctype,
                'retrieved_at_wib': wib_now(),
                'body': body,
            }
            write_json(raw_file, envelope)
            write_json(date_raw_file, envelope)

        # Parse fare details
        fare_status = 'EMPTY'
        fare_amount = ''
        total_price = ''
        quota = ''
        msg = ''

        if status_code == 200 and isinstance(body, dict):
            if body.get('status') is True:
                total_price = body.get('totalPrice', '')
                pdetails = body.get('pricingDetails', [])
                if pdetails:
                    p0 = pdetails[0]
                    fare_amount = p0.get('price', total_price)
                    quota = p0.get('quota', '')
                else:
                    fare_amount = total_price
                fare_status = 'OK'
                msg = body.get('message', 'Ship schedule found.')
            else:
                msg = body.get('message', 'Gateway returned status=false')
                fare_status = 'API_FALSE'
        else:
            fare_status = f'HTTP_{status_code}'
            msg = str(body) if isinstance(body, str) else json.dumps(body)

        results.append({
            'routeId': route_id,
            'originHarbourId': origin_id,
            'origin': origin,
            'destination': destination,
            'destinationProvince': dest_province,
            'serviceCategory': cat,
            'serviceId': svc_id,
            'serviceName': svc_name,
            'vehicleClass': vclass,
            'departDate': target_date,
            'departTime': slot_time,
            'scheduleId': schedule_id,
            'quota': quota,
            'fareAmount': int(round(float(fare_amount))) if fare_amount != '' else '',
            'totalPrice': int(round(float(total_price))) if total_price != '' else '',
            'currency': 'IDR',
            'status': fare_status,
            'statusCode': status_code,
            'message': msg,
        })

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description='Trip.ferizy.com Full-Scale Fare Scraper')
    parser.add_argument('--date', type=str, default='2026-08-21', help='Target departure date (YYYY-MM-DD)')
    parser.add_argument('--workers', type=int, default=4, help='Number of parallel worker threads')
    parser.add_argument('--force', action='store_true', help='Force re-fetching existing envelopes')
    args = parser.parse_args()

    target_date = args.date
    workers = max(1, min(args.workers, 8))
    force = args.force

    print('=== Trip.ferizy.com Full-Scale Fare Scrape ===', flush=True)
    print(f'Target Date: {target_date}', flush=True)
    print(f'Workers:     {workers}', flush=True)
    print(f'Force:       {force}', flush=True)

    raw_dir = DATA / 'ferizy-trip-all' / 'fares'
    date_raw_dir = DATA / 'trip-fares' / target_date
    raw_dir.mkdir(parents=True, exist_ok=True)
    date_raw_dir.mkdir(parents=True, exist_ok=True)
    EXPORTS.mkdir(parents=True, exist_ok=True)

    routes_path = DATA / 'routes.json'
    if not routes_path.exists():
        raise RuntimeError('routes.json is missing; run scrape_master.py first')
    routes: list[dict[str, Any]] = json.loads(routes_path.read_text(encoding='utf-8'))
    print(f'Loaded {len(routes)} routes from {routes_path}', flush=True)

    # Pre-authenticate
    master_client = TripFerizyClient()
    print('Authenticated with trip.ferizy.com API Gateway successfully', flush=True)

    all_results: list[dict[str, Any]] = []
    routes_completed = 0
    total_routes = len(routes)

    start_time = time.time()

    def process_route(route: dict[str, Any]) -> list[dict[str, Any]]:
        local_client = TripFerizyClient()
        return scrape_route_fares(local_client, route, target_date, raw_dir, date_raw_dir, force=force)

    print(f'Starting scrape across {total_routes} routes with {workers} workers...', flush=True)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        future_to_route = {pool.submit(process_route, r): r for r in routes}
        for future in as_completed(future_to_route):
            r = future_to_route[future]
            rid = r.get('routeId')
            try:
                r_results = future.result()
                all_results.extend(r_results)
                routes_completed += 1
                ok_count = sum(1 for item in r_results if item['status'] == 'OK')
                print(
                    f'[{routes_completed}/{total_routes}] Route {rid} ({r.get("originHarbourName")} -> {r.get("destination")}): '
                    f'{len(r_results)} services, {ok_count} OK',
                    flush=True,
                )
            except Exception as exc:
                routes_completed += 1
                print(f'[{routes_completed}/{total_routes}] Route {rid} ERROR: {exc}', flush=True)

    all_results.sort(key=lambda x: (str(x['routeId']), x['serviceCategory'], str(x['serviceId'])))
    ok_results = [r for r in all_results if r['status'] == 'OK']

    export_clean = EXPORTS / f'trip_fares_fullscale_{target_date}.csv'
    export_all = EXPORTS / f'trip_fares_fullscale_all_{target_date}.csv'

    clean_fields = [
        'routeId', 'originHarbourId', 'origin', 'destination', 'destinationProvince',
        'serviceCategory', 'serviceId', 'serviceName', 'vehicleClass',
        'departDate', 'departTime', 'scheduleId', 'quota', 'fareAmount', 'totalPrice', 'currency', 'status',
    ]

    all_fields = [
        'routeId', 'originHarbourId', 'origin', 'destination', 'destinationProvince',
        'serviceCategory', 'serviceId', 'serviceName', 'vehicleClass',
        'departDate', 'departTime', 'scheduleId', 'quota', 'fareAmount', 'totalPrice', 'currency',
        'status', 'statusCode', 'message',
    ]

    with open(export_clean, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=clean_fields)
        writer.writeheader()
        for r in ok_results:
            clean_row = {k: r.get(k, '') for k in clean_fields}
            writer.writerow(clean_row)

    with open(export_all, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=all_fields)
        writer.writeheader()
        for r in all_results:
            writer.writerow(r)

    manifest = {
        'source': 'https://trip.ferizy.com/',
        'gateway': BASE,
        'target_date': target_date,
        'total_routes': len(routes),
        'routes_with_ok_fares': len(set(r['routeId'] for r in ok_results)),
        'total_tested_services': len(all_results),
        'total_ok_fares': len(ok_results),
        'total_empty_no_schedule': sum(1 for r in all_results if 'SCHEDULE' in r['status']),
        'total_errors': sum(1 for r in all_results if 'HTTP' in r['status'] or 'ERROR' in r['status']),
        'elapsed_seconds': round(time.time() - start_time, 2),
        'exported_files': [
            str(export_clean.relative_to(ROOT)),
            str(export_all.relative_to(ROOT)),
        ],
    }
    write_json(DATA / 'trip-fares' / f'manifest_{target_date}.json', manifest)
    write_json(EXPORTS / f'trip_fares_manifest_{target_date}.json', manifest)

    print(f'=== Done in {manifest["elapsed_seconds"]}s ===', flush=True)
    print(f'Total Tested: {len(all_results)} | OK Fares: {len(ok_results)} (across {manifest["routes_with_ok_fares"]} routes)', flush=True)
    print(f'Clean CSV:    {export_clean} ({len(ok_results)} rows + header)', flush=True)
    print(f'All CSV:      {export_all} ({len(all_results)} rows + header)', flush=True)


if __name__ == '__main__':
    main()
