#!/usr/bin/env python3
"""Fetch remaining public Ferizy master endpoints not yet covered."""
from __future__ import annotations
import json, time
from pathlib import Path
from scrape_master import BASE, DATA, FerizyClient, record_response, wib_now

ROOT = Path('/home/fadil/trip-ferizy-scrape')
OUT = DATA / 'misc_public'
OUT.mkdir(parents=True, exist_ok=True)

# Public endpoints derived from raw JS, excluding AUTH group
# These were not in the original scrape_master public_specs
TARGETS = [
    ('homepage_layanan', '/ferizy/homepage/layanan', {}),
    ('homepage_range_age', '/ferizy/homepage/range/age', {}),
    ('homepage_service_type_global', '/ferizy/homepage/service-type', {}),
    ('homepage_verification', '/ferizy/homepage/verification', {}),
    ('homepage_vaccine_reason_global', '/ferizy/homepage/vaccine/reason', {}),
    ('homepage_vaccine_self_assesment_global', '/ferizy/homepage/vaccine/self-assesment', {}),
    ('configuration_check', '/ferizy/configuration/check', {}),
    ('configuration_parameterize_sample', '/ferizy/configuration/parameterize', {'AIFParameterName': 'popup_banner_link'}),
    ('check_mitra', '/ferizy/check-mitra', {}),
    # logistic public master data
    ('logistic_cargo_category', '/ferizy/logistic/cargo-category', {}),
    ('logistic_form_parameter_setting', '/ferizy/logistic/form-parameter-setting', {}),
    ('logistic_list_cargo_type', '/ferizy/logistic/list-cargo-type', {}),
    ('logistic_list_city', '/ferizy/logistic/list-city', {}),
    ('logistic_list_comodity', '/ferizy/logistic/list-comodity', {}),
    ('logistic_list_industry_type', '/ferizy/logistic/list-industry-type', {}),
    ('logistic_list_item_owner', '/ferizy/logistic/list-item-owner', {}),
    ('logistic_list_item_receiver', '/ferizy/logistic/list-item-receiver', {}),
    ('logistic_list_logistic_company', '/ferizy/logistic/list-logistic-company', {}),
    ('logistic_quickpick', '/ferizy/logistic/quickpick', {}),
    ('logistic_setting_param', '/ferizy/logistic/setting-param', {}),
    # payment / ticket public-ish
    ('payment_options', '/ferizy/payment/options', {}),
    ('ticket_parameter_sample', '/ferizy/ticket/parameter', {'AIFParameterName': 'informasi_penting'}),
]

def main():
    client = FerizyClient()
    print('authenticated for misc public')
    results = []
    for name, path, extra in TARGETS:
        try:
            status, ctype, payload = client.request('GET', path, extra=extra, max_attempts=3, timeout=30)
            record_response(OUT / f'{name}.json', status, ctype, payload, {'method':'GET','url':BASE+path,'headers_extra':extra})
            print(f'{name} status={status}')
            results.append({'name':name,'path':path,'status':status})
        except Exception as exc:
            print(f'{name} FAILED {exc!r}')
            # still record failure
            try:
                record_response(OUT / f'{name}.json', 0, '', str(exc), {'method':'GET','url':BASE+path,'headers_extra':extra,'error':repr(exc)})
            except Exception:
                pass
            results.append({'name':name,'path':path,'status':0,'error':repr(exc)})
        time.sleep(0.8)

    (ROOT / 'misc_public_manifest.json').write_text(json.dumps({'retrieved_at_wib': wib_now(), 'requested': len(TARGETS), 'results': results}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'requested':len(TARGETS),'ok_200':sum(1 for r in results if r.get('status')==200)}, indent=2))

if __name__ == '__main__':
    main()
