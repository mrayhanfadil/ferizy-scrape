# Ferizy Public Scrape — Unified (`trip.ferizy.com` + `ferizy.com`)

Defensive-only scrape of **ASDP Ferizy** public master data. Two portals, one unified dataset. **No authenticated / personal / order / payment data**.

> **Retrieved:** `2026-08-19T12:18:45+07:00` (WIB) · **Sources:** `https://trip.ferizy.com/` (Nuxt + `api-gateway-1.ferizy.com`) + `https://ferizy.com/` (classic PHP) · **Archive:** `ferizy-unified-scrape.zip` — **629 files, 3.18 MB sanitized**

## Why two portals?

The `select2` dropdown you flagged (`Bakauheni, Lampung / Gilimanuk, Bali / Ketapang, Jawa Timur / Merak, Banten / Pelabuhan Lainnya? → https://trip.ferizy.com`) is from `ferizy.com`. That's the **classic** portal (west corridor). `trip.ferizy.com` is the **new** API-Gateway portal (65 eastern/central origins, 140 routes). They are separate systems — this repo merges both.

`GET https://ferizy.com/schedule/init` (verified):
```json
{"origin":[
  {"id":"3","text":"Bakauheni, Lampung"},
  {"id":"4","text":"Gilimanuk, Bali"},
  {"id":"5","text":"Ketapang, Jawa Timur"},
  {"id":"2","text":"Merak, Banten"},
  {"id":99,"text":"Pelabuhan Lainnya?, Klik Disini","url":"https://trip.ferizy.com","is_redirect":true}
]}
```

## Counts

| Portal | Origins | Directed OD | OD × Ship | Notes |
|---|---:|---:|---:|---|
| **trip.ferizy.com** | **65** | **140** | 140 service_type (56 checkin OK / 84 `Data not found`) | Sulawesi/NTT/Maluku/Kalimantan/Bali-NTB etc. |
| **ferizy.com (classic)** | **4** | **4** | **6** | `Merak ↔ Bakauheni` (Express+Reguler), `Gilimanuk ↔ Ketapang` (Reguler) |
| **Unified** | **69** | **146** | — | Deduplicated harbours, `classic-*` IDs for classic |

Other unified totals: **2,028** service detail rows · **4,513** check-in schedule rows · **19** parameter files · **14** crawled pages · **4** media · **22** misc public probes (5 × HTTP 200) · **9** live fare rows (classic, 2026-08-20).

## File layout

```
trip-ferizy-scrape/                  ← canonical live folder (this repo)
├── data/                            ← raw trip.ferizy.com API envelopes
│   ├── homepage_origin.json         ← 65 origins
│   ├── routes.json                  ← 140 routes (SUMMARY 0 failures)
│   ├── destinations/<harbourId>.json← 65 destination lists
│   ├── route_details/<routeId>/
│   │   ├── service_type.json        ← 140/140 HTTP 200
│   │   └── checkin.json             ← 56 OK / 84 Data not found
│   ├── misc_public/*.json           ← 22 probes (5 OK: homepage/range/age, homepage/service-type, vaccine/self-assesment, logistic/form-parameter-setting, ticket/parameter)
│   ├── parameters/*.json            ← 19
│   └── ferizy-classic/              ← 33 classic raw JSON (init, route_origin_*, ship_class_*, times_*, timesandkuota_*, fare_*)
├── exports/
│   ├── origins.csv                  ← 65 trip origins (harbourId,harbourName,province)
│   ├── routes.csv                   ← 140 trip routes (routeId,originHarbourId,originHarbourName,originProvince,origin,destination,destinationProvince)
│   ├── service_types.csv            ← 2,028 rows (routeId, serviceCategory, serviceName, …)
│   ├── checkin_schedules.jsonl      ← 4,513 rows (one schedule per line)
│   ├── parameters.csv               ← 19 rows
│   ├── unified_origins.csv          ← 69 (adds classic Bakauheni/Merak/Gilimanuk/Ketapang as classic-3/2/4/5)
│   ├── unified_routes.csv           ← 146 (140 trip + 6 classic `classic-{o}-{d}-{ship}`)
│   ├── unified_fares_ferizy_classic.csv ← 9 live fares 2026-08-20 (see below)
│   └── ferizy-classic/ferizy_classic_routes.csv ← 6 OD×Ship
├── pages/                           ← 14 static page snapshots
├── media/                           ← 4 assets
├── raw/                             ← _nuxt entry 84d59672.js + chunks (AIFSignature slice 379745..381033 preserved)
├── final_manifest.json              ← unified counts + file map + limitations
├── scrape_master.py                 ← trip.ferizy.com master (origin→destination→service/checkin, retry 5×, checkpoint each response)
├── scrape_route_metadata*.py        ← trip route metadata (fast/4workers variants)
├── scrape_public_parameters.py
├── scrape_misc_public.py
└── crawl_pages.py
```

Classic-only mirror (prior to merge) preserved at `~/ferizy-scrape/` — already merged into `data/ferizy-classic/` and `exports/ferizy-classic/`.

## Main exports — schema

**`exports/unified_origins.csv`** — `harbourId,harbourName,province,source` (`source` = `trip.ferizy.com` | `ferizy.com`)

**`exports/unified_routes.csv`** — `routeId,origin,destination,shipClass,source,originHarbourId,destinationProvince` (`routeId` = trip numeric or `classic-{o}-{d}-{ship}`; `shipClass` empty for trip, `Express`/`Reguler` for classic)

**`exports/unified_fares_ferizy_classic.csv`** — `origin,destination,shipClass,vehicleClass,departDate,departTime,kuota,fareAmount,totalFare,currency,sourceFile`

**`exports/service_types.csv`** — trip service metadata (Pejalan Kaki / Kendaraan, Gol I–IX, Dewasa/Anak/Bayi)

**`exports/checkin_schedules.jsonl`** — trip check-in windows (`tanggalMulai/tanggalSelesai` + `data[]: {dateDeparture,timeDeparture,scheduleId}`)

## Live fare — Bakauheni ↔ Merak Gol 5 (verified 2026-08-20)

Via `POST https://ferizy.com/schedule` with encrypted `window.searchData.data` (passphrase `60b858fe8ae649057bb997c4`, `ship_schedule?origin=…&vehicle_class=…` → `window.searchData.data` → decrypt server-side). Sample `data/fare_3_2_2_vc11_2026-08-20.json`:

| Route | Layanan | GOL VA (<7 m penumpang) | GOL VB (<7 m barang) | Kuota | Slot |
|---|---:|---:|---:|---:|---|
| **Bakauheni → Merak Express** | Express (id 2) | **Rp 1.225.928** | **Rp 904.923** | 400 | 00:18 discrete |
| **Merak → Bakauheni Express** | Express (id 2) | **Rp 1.225.928** | **Rp 904.923** | 400 | 00:54 discrete |
| Bakauheni → Merak Reguler | Reguler (id 1) | Rp 963.800 | Rp 835.300 | 1000 | 01:00–02:00 hourly |
| Gilimanuk → Ketapang Reguler | Reguler | Rp 420.400 | — | 399 | 01:00–02:00 |
| Ketapang → Gilimanuk Reguler | Reguler | Rp 420.400 | — | 600 | 01:00–02:00 |

Raw envelopes: `data/ferizy-classic/fare_*.json` + `data/ferizy-classic/timesandkuota_*.json` + `data/ferizy-classic/times_*.json`.

Schedule shape: **Express** = 38–39 discrete departures/day (00:15, 00:18, 00:54, 01:30 …), kuota 400. **Reguler** = 24 hourly windows (00:00–01:00 … 23:00–24:00), kuota 1000 (Bali 399/600).

## Reproduce

```bash
# trip.ferizy.com — public masters (needs no auth; AIFSignature via openssl AES-128-ECB)
python3 scrape_master.py                  # 65 origins → 140 routes (checkpointed)
python3 scrape_route_metadata_fast.py     # service_type + checkin per route (ThreadPool 2)
python3 scrape_public_parameters.py       # 19 params
python3 scrape_misc_public.py             # 22 extra public endpoints
python3 crawl_pages.py                    # 14 static pages

# ferizy.com classic — west corridor + live fares (already merged, but re-runnable)
# see ~/ferizy-scrape scrape (schedule/init → schedule/route → schedule/ship_class → schedule/times → schedule/timesandkuota → ship_schedule → POST /schedule)
```

Requirements: Python 3 + `requests`, `openssl` CLI (`enc -aes-128-ecb -K <hex> -a -A` for `AIFSignature` with key `61643163343938653932313434326366`). Headers: `AIFClient`, `AIFSignature`, `Referer: https://trip.ferizy.com/`, `Connection: close`, retry `min(2*attempt,10)s`.

## Scope & sanitization

* **Defensive-only:** only public portal HTML + public API master data. Checkpoint each response.
* **Excluded:** `account/*`, `etis/refund`, `etis/reschedule`, `ticket/order/*`, `logistic/order`, `payment/*` — all authenticated personal/order flows are intentionally not scraped.
* Archive sanitized: `psUsername`, `publicPath`, `etisdev`/`SGWASDP5`, `AIFClient`/`AIFSignature` values replaced with `[redacted]`/`[REDACTED]` before zipping (verified: no `auth-response`, no credentials).

## Limitations

* `ticket/ship/schedule` price/quota/availability are **dynamic** (route + date/time + service + vehicle class + live quota). No single static “all fares” table exists — exhaustive scrape requires a caller-defined fare matrix (route × date × serviceId × vehicleClass).
* Several probed public paths return `400/404/408` without required params/auth (`homepage/layanan`, `homepage/verification`, `logistic/list-*`, etc.) — error envelopes archived but contain no dataset.
* `configuration/check` is unstable (`RemoteDisconnected`) on this gateway at scrape time.

## Tech

* Portal: `trip.ferizy.com/_nuxt/entry.84d59672.js` (AIF logic slice `const lL=` → `var Wc=` bytes 379745..381033, 1288 B → `/tmp/ferizy-part.js` + base64)
* Classic: `ferizy.com/assets/js/pages/getfare.js` + `ship_schedule.js` (`BASE_URL + "schedule"` with `data=<encrypted base64>`)
* Gateway: `https://api-gateway-1.ferizy.com` (trip) · `https://ferizy.com/schedule/*` (classic)

## License

Dataset is a snapshot of **publicly accessible** ASDP Ferizy data for research/audit. Not affiliated with ASDP. Respect `robots.txt` and rate limits. No personal data included.
