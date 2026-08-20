# Ferizy Public Scrape — Unified (`trip.ferizy.com` + `ferizy.com`)

Defensive-only scrape of **ASDP Ferizy** public master data. Two portals, one unified dataset. **No authenticated / personal / order / payment data**.

- **Live Explorer:** https://ferizy-explorer.pages.dev
- **Retrieved:** `2026-08-19T12:18:45+07:00` (WIB) · **Sources:** `https://trip.ferizy.com/` (Nuxt + `api-gateway-1.ferizy.com`) + `https://ferizy.com/` (classic PHP) · **Archive:** `ferizy-unified-scrape.zip` — **629 files, 3.18 MB sanitized**

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
| **trip.ferizy.com** | **65** | **140** | 140 service_type (56 checkin OK / 84 `Data not found`) | Sulawesi/NTT/Maluku/Kalimantan/Bali-NTB etc. · 593 live fares (39 routes, 2026-08-21) |
| **ferizy.com (classic)** | **4** | **4** | **6** | `Merak ↔ Bakauheni` (Express+Reguler), `Gilimanuk ↔ Ketapang` (Reguler) · 72 live fares (6 OD×Ship ×12 VC, 2026-08-20) |
| **Unified** | **69** | **146** | — | Deduplicated harbours, `classic-*` IDs for classic |

Other unified totals: **2,028** service detail rows · **4,513** check-in schedule rows · **19** parameter files · **14** crawled pages · **4** media · **22** misc public probes (5 × HTTP 200) · **72** live fare rows (classic, 2026-08-20) · **593** live fare rows (trip, 2026-08-21 across 39 routes / 2,031 tested service rows).

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
│   ├── trip-fares/
│   │   ├── 2026-08-21/              ← checkpointed raw trip fare JSON envelopes (fare_<routeId>_s<serviceId>.json)
│   │   └── manifest_2026-08-21.json ← trip fare snapshot summary manifest
│   ├── ferizy-trip-all/
│   │   └── fares/                   ← checkpointed raw trip fare JSON envelopes (fare_<routeId>_s<serviceId>_2026-08-21.json)
│   ├── ferizy-classic-all/          ← 72 full matrix fare JSON envelopes
│   └── ferizy-classic/              ← 96 classic raw JSON (init, route_origin_*, ship_class_*, times_*, timesandkuota_*, fare_*)
├── exports/
│   ├── origins.csv                  ← 65 trip origins (harbourId,harbourName,province)
│   ├── routes.csv                   ← 140 trip routes (routeId,originHarbourId,originHarbourName,originProvince,origin,destination,destinationProvince)
│   ├── service_types.csv            ← 2,028 rows (routeId, serviceCategory, serviceName, …)
│   ├── checkin_schedules.jsonl      ← 4,513 rows (one schedule per line)
│   ├── parameters.csv               ← 19 rows
│   ├── unified_origins.csv          ← 69 (adds classic Bakauheni/Merak/Gilimanuk/Ketapang as classic-3/2/4/5)
│   ├── unified_routes.csv           ← 146 (140 trip + 6 classic `classic-{o}-{d}-{ship}`)
│   ├── unified_fares_ferizy_classic.csv ← 72 live fares (73 lines with header) 2026-08-20 (see below)
│   ├── unified_fares_ferizy_classic_all_2026-08-20.csv ← 144 test matrix (72 OK / 72 empty Pejalan Kaki)
│   ├── trip_fares_fullscale_2026-08-21.csv ← 593 live fares (594 lines with header) 2026-08-21 (39 routes)
│   ├── trip_fares_fullscale_all_2026-08-21.csv ← 2,031 tested service rows across 140 routes with source status
│   ├── trip_fares_manifest_2026-08-21.json ← trip fare run manifest
│   └── ferizy-classic/ferizy_classic_routes.csv ← 6 OD×Ship
├── pages/                           ← 14 static page snapshots
├── media/                           ← 4 assets
├── raw/                             ← _nuxt entry 84d59672.js + chunks (AIFSignature slice 379745..381033 preserved)
├── scripts/
│   ├── scrape_fares_all_vehicle_classes.py ← classic 3-step pipeline scraper (timesandkuota→ship_schedule→schedule)
│   └── scrape_fares_trip_fullscale.py      ← trip full-scale scraper (140 routes, HMAC-SHA512 AIFSignature, retry/checkpoint)
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

**`exports/unified_fares_ferizy_classic_all_2026-08-20.csv`** — full 144 test matrix with `status,statusCode,message` (72 OK / 72 empty Pejalan Kaki combos / 0 failed)

**`exports/trip_fares_fullscale_2026-08-21.csv`** — `routeId,originHarbourId,origin,destination,destinationProvince,serviceCategory,serviceId,serviceName,vehicleClass,departDate,departTime,scheduleId,quota,fareAmount,totalPrice,currency,status` (593 live fare rows across 39 routes)

**`exports/trip_fares_fullscale_all_2026-08-21.csv`** — `routeId,originHarbourId,origin,destination,destinationProvince,serviceCategory,serviceId,serviceName,vehicleClass,departDate,departTime,scheduleId,quota,fareAmount,totalPrice,currency,status,statusCode,message` (2,031 tested service rows across all 140 routes with raw API status: 593 OK, 998 SCHEDULE_DATA_NOT_FOUND, 430 NO_SCHEDULE_FOR_DATE, 7 HTTP_400, 3 NO_SERVICE_TYPES)

**`exports/trip_fares_manifest_2026-08-21.json`** & **`data/trip-fares/manifest_2026-08-21.json`** — metadata and summary tallies of the trip fare run.

**`exports/service_types.csv`** — trip service metadata (Pejalan Kaki / Kendaraan, Gol I–IX, Dewasa/Anak/Bayi)

**`exports/checkin_schedules.jsonl`** — trip check-in windows (`tanggalMulai/tanggalSelesai` + `data[]: {dateDeparture,timeDeparture,scheduleId}`)

## Live fare — full 12 Golongan (verified 2026-08-20)

| Golongan | Description | Bakauheni → Merak (Express) | Bakauheni → Merak (Reguler) | Gilimanuk → Ketapang (Reguler) |
|---|---|---:|---:|---:|
| GOLONGAN I | Sepeda Kayuh | Rp 85.000 | Rp 26.500 | Rp 11.000 |
| GOLONGAN II | Sepeda Motor <500cc | Rp 129.677 | Rp 62.100 | Rp 31.600 |
| GOLONGAN III | Sepeda Motor >500cc / Roda 3 | Rp 187.853 | Rp 133.000 | Rp 45.000 |
| GOLONGAN IVA | Penumpang <5m | Rp 749.128 | Rp 481.800 | Rp 213.400 |
| GOLONGAN IVB | Barang <5m | Rp 491.800 | Rp 447.800 | Rp 182.400 |
| GOLONGAN VA | Penumpang <7m | Rp 1.225.928 | Rp 963.800 | Rp 420.400 |
| GOLONGAN VB | Barang <7m | Rp 904.923 | Rp 835.300 | Rp 309.500 |
| GOLONGAN VIA | Penumpang <10m | Rp 2.015.985 | Rp 1.594.800 | Rp 637.800 |
| GOLONGAN VIB | Barang <10m | Rp 1.366.620 | Rp 1.285.200 | Rp 511.100 |
| GOLONGAN VII | Tronton <12m | Rp 1.975.580 | Rp 1.860.400 | Rp 630.300 |
| GOLONGAN VIII | Gandeng <16m | Rp 2.619.845 | Rp 2.452.400 | Rp 888.300 |
| GOLONGAN IX | Gandeng >16m | Rp 3.998.920 | Rp 3.755.000 | Rp 1.229.600 |

Raw envelopes: `data/ferizy-classic-all/fares/fare_*.json` + `data/ferizy-classic/fare_*.json` (72 JSON files). Pipeline: 3-step `POST /schedule/timesandkuota` → `GET /ship_schedule` → `POST /schedule` with dynamic slot selection.

## Trip full-scale fare snapshot (verified 2026-08-21)

| Metric | Result |
|---|---:|
| Trip routes enumerated | 140 / 140 |
| Service rows tested | 2,031 |
| Live fare rows (`OK`) | 593 |
| Routes with at least one live fare | 39 |
| `SCHEDULE_DATA_NOT_FOUND` | 998 |
| `NO_SCHEDULE_FOR_DATE` | 430 |
| `HTTP_400` source responses | 7 |
| `NO_SERVICE_TYPES` | 3 |
| Scrape errors | 0 after route 5515 retry |

`Kendaraan` rows cover each route's exposed vehicle service definitions (GOL I/II/III/IVA/IVB/VA/VB/VIA/VIB/VII/VIII/IX); passenger services such as DEWASA/BAYI are included when exposed. Do not label it a universal tariff table. The public endpoint exposes live fares for 39 routes on this snapshot date (2026-08-21); the remaining 101 routes are explicitly retained with their source status codes (`SCHEDULE_DATA_NOT_FOUND`, `NO_SCHEDULE_FOR_DATE`, `HTTP_400`, `NO_SERVICE_TYPES`) because pricing and schedules on `trip.ferizy.com` are volatile and schedule-dependent.

| Route | Service rows OK | Example fares |
|---|---:|---|
| Kayangan → Pototano (route 29) | 14 | GOL I Rp32,000; GOL IVA Rp563,000; GOL IX Rp2,265,000; Dewasa Rp18,800 |
| Lembar → Padang Bai (route 25) | 14 | GOL I Rp81,600; GOL IVA Rp1,184,100; GOL IX Rp8,265,800; Dewasa Rp65,300 |

> [!NOTE]
> **Fare Snapshot Limitations:** Fares, quotas, and ship schedules are dynamic and dependent on departure date, departure time, route, and service type. The date `2026-08-21` represents a specific point-in-time snapshot; non-OK status codes reflect raw source API responses and must not be interpreted as free or zero-price routes. No authenticated, customer, order, or payment data was requested or scraped.

## Reproduce

```bash
# trip.ferizy.com — public masters (needs no auth; AIFSignature via openssl AES-128-ECB)
python3 scrape_master.py                  # 65 origins → 140 routes (checkpointed)
python3 scrape_route_metadata_fast.py     # service_type + checkin per route (ThreadPool 2)
python3 scrape_public_parameters.py       # 19 params
python3 scrape_misc_public.py             # 22 extra public endpoints
python3 crawl_pages.py                    # 14 static pages

# trip.ferizy.com — full-scale fare snapshot (140 routes, HMAC-SHA512 AIFSignature, checkpointed)
python3 scripts/scrape_fares_trip_fullscale.py

# ferizy.com classic — west corridor + live fares (already merged, but re-runnable)
# see ~/ferizy-scrape scrape (schedule/init → schedule/route → schedule/ship_class → schedule/times → schedule/timesandkuota → ship_schedule → POST /schedule)
python3 scripts/scrape_fares_all_vehicle_classes.py
```

Requirements: Python 3 + `requests`, `cryptography` (for AES-128-CBC / token crypto) or `openssl` CLI (`enc -aes-128-ecb -K <hex> -a -A` for legacy `AIFSignature` with key `61643163343938653932313434326366`). Headers: `AIFClient`, `AIFSignature`, `Referer: https://trip.ferizy.com/`, `Connection: close`, retry `min(2*attempt,10)s`.

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
