#!/usr/bin/env python3
"""Fetch the portal's public parameter/configuration text endpoints."""
from __future__ import annotations

import json
import time
from pathlib import Path

from scrape_master import BASE, DATA, FerizyClient, record_response, timestamp, wib_now, write_json

ROOT = Path('/home/fadil/trip-ferizy-scrape')
OUT = DATA / 'parameters'
OUT.mkdir(parents=True, exist_ok=True)

# Names observed in the public Nuxt bundle. Special names use their own API path.
PARAMETERS = {
    'alasan_belum_memenuhi_verifikasi_antigen': ('/ferizy/homepage/vaccine/reason', 'AIFParameterName'),
    'alasan_belum_memenuhi_verifikasi_vaksin': ('/ferizy/homepage/vaccine/reason', 'AIFParameterName'),
    'belum_memenuhi_ketentuan_perjalanan': ('/ferizy/homepage/verification', 'AIFParameterName'),
    'detail_informasi_pembatalan_refund_reschedule': ('/ferizy/ticket/parameter', 'AIFParameterName'),
    'expired_option_payment': ('/ferizy/ticket/parameter', 'AIFParameterName'),
    'expired_payment': ('/ferizy/ticket/parameter', 'AIFParameterName'),
    'expired_verification': ('/ferizy/ticket/parameter', 'AIFParameterName'),
    'halaman_order_popup_himbauan': ('/ferizy/ticket/parameter', 'AIFParameterName'),
    'halaman_pencarian_jadwal_kebijakan': ('/ferizy/ticket/parameter', 'AIFParameterName'),
    'informasi_pembatalan_refund_reschedule': ('/ferizy/ticket/parameter', 'AIFParameterName'),
    'informasi_penting': ('/ferizy/ticket/parameter', 'AIFParameterName'),
    'informasi_syarat_dan_ketentuan': ('/ferizy/ticket/parameter', 'AIFParameterName'),
    'ketentuan_perjalanan_pencarian_jadwal_content': ('/ferizy/homepage/vaccine/self-assesment', 'AIFParameterName'),
    'persetujuan_ketentuan_penggunaan_data_diri': ('/ferizy/ticket/parameter', 'AIFParameterName'),
    'popup_banner_link': ('/ferizy/ticket/parameter', 'AIFParameterName'),
    'self_assesment_ketentuan_perjalanan': ('/ferizy/homepage/vaccine/reason', 'AIFParameterName'),
    'self_assesment_syarat_perjalanan': ('/ferizy/ticket/parameter', 'AIFParameterName'),
    'syarat_ketentuan_jadwal_masuk_pelabuhan': ('/ferizy/ticket/parameter', 'AIFParameterName'),
    'waktu_verifikasi_telah_habis': ('/ferizy/ticket/parameter', 'AIFParameterName'),
}


def main() -> None:
    client = FerizyClient()
    manifest = {'started_at_wib': wib_now(), 'requested': len(PARAMETERS), 'ok': 0, 'failures': []}
    for index, (name, (path, header_name)) in enumerate(PARAMETERS.items(), start=1):
        extra = {header_name: name}
        try:
            status, ctype, payload = client.request('GET', path, extra=extra)
            record_response(OUT / f'{name}.json', status, ctype, payload, {
                'method': 'GET', 'url': BASE + path,
                'parameter': name, 'headers_extra': extra,
            })
            if status == 200:
                manifest['ok'] += 1
            else:
                manifest['failures'].append({'name': name, 'status': status})
            print(f'parameter {index}/{len(PARAMETERS)} {name} status={status}')
        except Exception as exc:
            manifest['failures'].append({'name': name, 'error': repr(exc)})
            print(f'parameter {index}/{len(PARAMETERS)} {name} FAILED')
        time.sleep(1)

    # The three known public bulk values are also captured with the rest.
    manifest['finished_at_wib'] = wib_now()
    write_json(ROOT / 'parameter_manifest.json', manifest)
    print(json.dumps({'requested': manifest['requested'], 'ok': manifest['ok'], 'failures': len(manifest['failures'])}))


if __name__ == '__main__':
    main()
