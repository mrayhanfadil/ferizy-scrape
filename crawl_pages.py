#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests

ROOT = Path('/home/fadil/trip-ferizy-scrape')
OUT = ROOT / 'pages'
OUT.mkdir(parents=True, exist_ok=True)
BASE = 'https://trip.ferizy.com/'
PATHS = [
    '/', '/ferryschedule', '/vehicle-class', '/privacy-policy', '/termsandconditions',
    '/signin', '/signup', '/signup/passwordrecovery', '/maintenance', '/misc/config', '/misc/qrcode',
    '/robots.txt', '/sitemap.xml', '/manifest.json',
]
S = requests.Session()
S.headers.update({'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36'})
manifest = []
for path in PATHS:
    url = urljoin(BASE, path.lstrip('/')) if path != '/' else BASE
    try:
        r = S.get(url, timeout=30)
        name = 'root.html' if path == '/' else path.strip('/').replace('/', '__') + '.html'
        (OUT / name).write_bytes(r.content)
        text = r.text
        manifest.append({
            'path': path, 'url': url, 'status': r.status_code,
            'content_type': r.headers.get('content-type'), 'bytes': len(r.content),
            'title': (re.search(r'<title>(.*?)</title>', text, re.I | re.S) or [None, None])[1],
        })
        print(path, r.status_code, len(r.content))
    except Exception as exc:
        manifest.append({'path': path, 'url': url, 'error': repr(exc)})
        print(path, 'FAILED', type(exc).__name__)
(ROOT / 'page_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
