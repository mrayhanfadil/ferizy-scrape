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
| **trip.ferizy.com** | **65** | **140** | 140 service_type (56 checkin OK / 84 `Data not found`) | Sulawesi/NTT/Maluku/Kalimantan/Bali-NTB etc. · **3,700 live tariff rows** across 63 routes (7-day period snapshot 2026-08-20..2026-08-26; 14,005 matrix rows across all 140 routes) · 597 live fares single-day (2026-08-21) |
| **ferizy.com (classic)** | **4** | **4** | **6** | `Merak ↔ Bakauheni` (Express+Reguler), `Gilimanuk ↔ Ketapang` (Reguler) · 72 live fares (6 OD×Ship ×12 VC, 2026-08-20) |
| **Unified** | **69** | **146** | — | Deduplicated harbours, `classic-*` IDs for classic |

Other unified totals: **2,028** service detail rows · **4,513** check-in schedule rows · **19** parameter files · **14** crawled pages · **4** media · **22** misc public probes (5 × HTTP 200) · **72** live fare rows (classic, 2026-08-20) · **3,700** canonical period live tariff rows (trip 7-day union 2026-08-20..2026-08-26 across 63 routes / 14,005 period matrix rows across all 140 route IDs) · **597** single-day live fares (trip 2026-08-21 across 39 routes / 2,003 tested service rows).

## File layout

```
trip-ferizy-scrape/                  ← canonical live folder (this repo)
├── data/                            ← raw trip.ferizy.com API envelopes
│   ├── homepage_origin.json         ← 65 origins
│   ├── routes.json                  ← 140 routes (SUMMARY 0 failures)
│   ├── destinations/<harbourId>.json← 65 destination lists
│   ├── route_details/<routeId>/
│   │   ├── service_type.json        ← 140/140 HTTP 200
│   │   └── checkin.json             ← 56 OK / 84 Data not found (date-aware refreshed)
│   ├── misc_public/*.json           ← 22 probes (5 OK: homepage/range/age, homepage/service-type, vaccine/self-assesment, logistic/form-parameter-setting, ticket/parameter)
│   ├── parameters/*.json            ← 19
│   ├── trip-fares/
│   │   ├── 2026-08-20..2026-08-26/  ← checkpointed raw trip fare JSON envelopes (fare_<routeId>_s<serviceId>.json)
│   │   └── manifest_2026-08-20..2026-08-26.json ← daily run summary manifests
│   ├── ferizy-trip-all/
│   │   └── fares/                   ← checkpointed raw trip fare JSON envelopes (fare_<routeId>_s<serviceId>_<date>.json)
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
│   ├── trip_fares_snapshot_2026-08-20_2026-08-26.csv ← 3,700 live tariff rows (3,701 lines with header) 7-day period union
│   ├── trip_fares_snapshot_matrix_2026-08-20_2026-08-26.csv ← 14,005 tested matrix rows across all 140 routes with raw API status
│   ├── trip_fares_snapshot_2026-08-20_2026-08-26.json ← 7-day period summary manifest
│   ├── trip_fares_snapshot_missing_routes_2026-08-20_2026-08-26.json ← list of 77 routes without live schedules in 7-day window
│   ├── ferizy_all_fares_2026-08-20_2026-08-26.csv ← 3,772 normalized live tariffs (Trip + Classic, one file)
│   ├── ferizy_all_fares_matrix_2026-08-20_2026-08-26.csv ← 14,149 normalized matrix rows (Trip + Classic, one file)
│   ├── ferizy_all_fares_manifest_2026-08-20_2026-08-26.json ← unified export manifest
│   ├── ferizy_all_routes.csv     ← 146 normalized routes (140 Trip + 6 Classic, one file)
│   ├── trip_fares_fullscale_2026-08-21.csv ← 597 live fares single-day snapshot (39 routes)
│   ├── trip_fares_fullscale_all_2026-08-21.csv ← 2,003 tested service rows across 140 routes single-day
│   ├── trip_fares_manifest_2026-08-21.json ← single-day run manifest
│   └── ferizy-classic/ferizy_classic_routes.csv ← 6 OD×Ship
├── pages/                           ← 14 static page snapshots
├── media/                           ← 4 assets
├── raw/                             ← _nuxt entry 84d59672.js + chunks (AIFSignature slice 379745..381033 preserved)
├── scripts/
│   ├── scrape_fares_all_vehicle_classes.py ← classic 3-step pipeline scraper (timesandkuota→ship_schedule→schedule)
│   ├── scrape_fares_trip_fullscale.py      ← trip full-scale scraper (140 routes, date-aware checkin invalidation, future-slot selection, cache validation)
│   ├── scrape_fares_trip_snapshot_range.py ← multi-day period snapshot runner and aggregator
│   └── merge_all_ferizy_fares.py            ← normalized Trip + Classic one-file merger
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

**`exports/unified_fares_ferizy_classic.csv`** — `origin,destination,shipClass,vehicleClass,departDate,departTime,kuota,fareAmount,totalFare,currency,sourceFile` (72 live fares)

**`exports/unified_fares_ferizy_classic_all_2026-08-20.csv`** — full 144 test matrix with `status,statusCode,message` (72 OK / 72 empty Pejalan Kaki combos / 0 failed)

**`exports/trip_fares_snapshot_2026-08-20_2026-08-26.csv`** — `date,routeId,originHarbourId,origin,destination,destinationProvince,serviceCategory,serviceId,serviceName,vehicleClass,departDate,departTime,scheduleId,quota,fareAmount,totalPrice,currency,status` (3,700 live tariff rows across 63 routes in the 7-day period union)

**`exports/ferizy_all_fares_2026-08-20_2026-08-26.csv`** — one normalized tariff CSV across both portals: **3,772 live rows** (3,700 Trip + 72 Classic). The `source` column is provenance only; the data is not split by portal.

**`exports/ferizy_all_fares_matrix_2026-08-20_2026-08-26.csv`** — one normalized full matrix across both portals: **14,149 rows** (14,005 Trip + 144 Classic), including `OK`, empty, and source-error statuses.

**`exports/ferizy_all_routes.csv`** — one normalized route master across both portals: **146 routes** (140 Trip + 6 Classic). Classic rows include numeric origin and destination harbour IDs; Trip rows retain the source route schema, where destination harbour IDs are not exposed by the public route export.

**`exports/trip_fares_snapshot_matrix_2026-08-20_2026-08-26.csv`** — `date,routeId,originHarbourId,origin,destination,destinationProvince,serviceCategory,serviceId,serviceName,vehicleClass,departDate,departTime,scheduleId,quota,fareAmount,totalPrice,currency,status,statusCode,message` (14,005 tested matrix rows across all 140 routes: 3,700 OK, 7,616 SCHEDULE_DATA_NOT_FOUND, 2,631 NO_SCHEDULE_FOR_DATE, 37 HTTP_400, 21 NO_SERVICE_TYPES)

**`exports/trip_fares_snapshot_2026-08-20_2026-08-26.json`** & **`exports/trip_fares_snapshot_missing_routes_2026-08-20_2026-08-26.json`** — 7-day range execution manifest and full list of 77 routes without published schedules in this window.

**`exports/trip_fares_fullscale_2026-08-21.csv`** — `routeId,originHarbourId,origin,destination,destinationProvince,serviceCategory,serviceId,serviceName,vehicleClass,departDate,departTime,scheduleId,quota,fareAmount,totalPrice,currency,status` (597 live fare rows across 39 routes for date 2026-08-21)

**`exports/trip_fares_fullscale_all_2026-08-21.csv`** — `routeId,originHarbourId,origin,destination,destinationProvince,serviceCategory,serviceId,serviceName,vehicleClass,departDate,departTime,scheduleId,quota,fareAmount,totalPrice,currency,status,statusCode,message` (2,003 tested service rows across all 140 routes single-day)

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

## Trip 7-day fare snapshot (2026-08-20 to 2026-08-26)

The canonical period-level dataset aggregates 7 consecutive daily full-scale scrape runs (`2026-08-20` through `2026-08-26`).

| Metric | Result |
|---|---:|
| Snapshot period | 2026-08-20 through 2026-08-26 (7 days) |
| Daily runs completed | 7 / 7 (100%) |
| Route IDs enumerated | 140 / 140 (100%) |
| Unique exposed route/service keys | 2,029 |
| Route/service keys with at least one live tariff (`OK`) | 959 |
| Unique exposed vehicle-service keys | 1,622 |
| Vehicle-service keys with at least one live tariff (`OK`) | 760 |
| Routes with at least one live tariff in period | 63 / 140 (45.0%) |
| Routes with no live tariff in period | 77 / 140 (55.0%) |
| Total period matrix rows tested | 14,005 |
| Total live tariff rows (`OK`) | 3,700 |
| `SCHEDULE_DATA_NOT_FOUND` responses | 7,616 |
| `NO_SCHEDULE_FOR_DATE` responses | 2,631 |
| `HTTP_400` source responses | 37 |
| `NO_SERVICE_TYPES` source responses | 21 |
| Scrape failures / unhandled errors | 0 |

### Daily Run Breakdown

| Date | Routes Tested | Routes with Live Fares | Tested Services | Live Fares (`OK`) | Empty / No Schedule | Source Errors | Daily Manifest |
|---|---:|---:|---:|---:|---:|---:|---|
| 2026-08-20 | 140 | 49 | 2,031 | 742 | 1,281 | 5 | [`exports/trip_fares_manifest_2026-08-20.json`](file:///home/fadil/trip-ferizy-scrape/exports/trip_fares_manifest_2026-08-20.json) |
| 2026-08-21 | 140 | 39 | 2,003 | 597 | 1,396 | 7 | [`exports/trip_fares_manifest_2026-08-21.json`](file:///home/fadil/trip-ferizy-scrape/exports/trip_fares_manifest_2026-08-21.json) |
| 2026-08-22 | 140 | 34 | 1,984 | 516 | 1,460 | 5 | [`exports/trip_fares_manifest_2026-08-22.json`](file:///home/fadil/trip-ferizy-scrape/exports/trip_fares_manifest_2026-08-22.json) |
| 2026-08-23 | 140 | 35 | 1,997 | 529 | 1,460 | 5 | [`exports/trip_fares_manifest_2026-08-23.json`](file:///home/fadil/trip-ferizy-scrape/exports/trip_fares_manifest_2026-08-23.json) |
| 2026-08-24 | 140 | 30 | 1,968 | 452 | 1,508 | 5 | [`exports/trip_fares_manifest_2026-08-24.json`](file:///home/fadil/trip-ferizy-scrape/exports/trip_fares_manifest_2026-08-24.json) |
| 2026-08-25 | 140 | 31 | 2,005 | 469 | 1,528 | 5 | [`exports/trip_fares_manifest_2026-08-25.json`](file:///home/fadil/trip-ferizy-scrape/exports/trip_fares_manifest_2026-08-25.json) |
| 2026-08-26 | 140 | 26 | 2,031 | 395 | 1,628 | 5 | [`exports/trip_fares_manifest_2026-08-26.json`](file:///home/fadil/trip-ferizy-scrape/exports/trip_fares_manifest_2026-08-26.json) |
| **Union** | **140** | **63** | **2,029 (unique)** | **3,700** | **10,247** | **58** | [`exports/trip_fares_snapshot_2026-08-20_2026-08-26.json`](file:///home/fadil/trip-ferizy-scrape/exports/trip_fares_snapshot_2026-08-20_2026-08-26.json) |

### Public Gateway Coverage & Limitations

> [!IMPORTANT]
> **Complete Public Snapshot Coverage, Not Universal Static Tariffs:**
> Do NOT interpret this dataset as claiming that every route has an active tariff. The 7-day period snapshot systematically probes all 140 route IDs and all 2,029 exposed vehicle/service definitions across every day of the observation window. The public gateway produced live tariffs for **63 routes** (totaling 3,700 live tariff observations).
>
> The remaining **77 routes** returned no active ship schedules, no service types, or valid source errors across all 7 days (`SCHEDULE_DATA_NOT_FOUND`: 7,616, `NO_SCHEDULE_FOR_DATE`: 2,631, `HTTP_400`: 37, `NO_SERVICE_TYPES`: 21). This reflects the reality of ASDP Ferizy's public booking portal: fares on `trip.ferizy.com` are volatile, schedule-dependent departure slots rather than universal static price sheets.
>
> The complete list of 77 routes with zero live tariffs during this period is exported to [`exports/trip_fares_snapshot_missing_routes_2026-08-20_2026-08-26.json`](file:///home/fadil/trip-ferizy-scrape/exports/trip_fares_snapshot_missing_routes_2026-08-20_2026-08-26.json):
> `1023206`, `106113`, `1407`, `174191`, `174531`, `177342`, `198563`, `198568`, `199436`, `199477`, `199478`, `199559`, `200201`, `200436`, `201027`, `201200`, `202204`, `208211`, `27`, `284296`, `296284`, `296300`, `31383`, `344049`, `35`, `40`, `42`, `436199`, `436200`, `441440`, `46`, `479541`, `5335`, `5350`, `5355`, `5363`, `5369`, `5373`, `5378`, `5408`, `5409`, `5410`, `5411051`, `5414`, `5415`, `5417`, `5418`, `5422`, `5425`, `5426`, `5427`, `5430`, `5431`, `5432`, `5433`, `5434`, `5435`, `5436`, `5437`, `5438`, `5439`, `5442`, `5443`, `5471`, `5476`, `5488`, `55057`, `55059`, `5513`, `5514`, `5515`, `5641003`, `5641004`, `5641005`, `58`, `83313`, `91`.

### Scraper Production Architecture

The updated scraper [`scripts/scrape_fares_trip_fullscale.py`](file:///home/fadil/trip-ferizy-scrape/scripts/scrape_fares_trip_fullscale.py) and range wrapper [`scripts/scrape_fares_trip_snapshot_range.py`](file:///home/fadil/trip-ferizy-scrape/scripts/scrape_fares_trip_snapshot_range.py) include key defensive features:
1. **Date-Aware Check-in Cache Invalidation:** `get_checkin_schedules` automatically verifies that cached `checkin.json` envelopes contain departure slots for the requested `target_date`, refreshing against the live API whenever the cache is stale.
2. **Current-Day Future-Slot Selection:** For current-day scraping, avoids expired midnight slots by selecting the earliest valid future slot where `timeDeparture >= now_hhmm`.
3. **Schedule-Matched Fare-Cache Validation:** Checkpoint validation strictly verifies `departure.date`, `departure.scheduleId`, and `departure.time` before accepting cached fare responses.

## Trip single-day fare snapshot (historical reference: 2026-08-21)

| Metric | Result |
|---|---:|
| Trip routes enumerated | 140 / 140 |
| Service rows tested | 2,003 |
| Live fare rows (`OK`) | 597 |
| Routes with at least one live fare | 39 |
| `SCHEDULE_DATA_NOT_FOUND` | 1,083 |
| `NO_SCHEDULE_FOR_DATE` | 313 |
| `HTTP_400` source responses | 7 |
| `NO_SERVICE_TYPES` | 3 |
| Scrape errors | 0 |

| Route | Service rows OK | Example fares |
|---|---:|---|
| Kayangan → Pototano (route 29) | 14 | GOL I Rp32,000; GOL IVA Rp563,000; GOL IX Rp2,265,000; Dewasa Rp18,800 |
| Lembar → Padang Bai (route 25) | 14 | GOL I Rp81,600; GOL IVA Rp1,184,100; GOL IX Rp8,265,800; Dewasa Rp65,300 |

## Reproduce

```bash
# trip.ferizy.com — 7-day snapshot range runner (aggregates daily runs + exports clean & matrix union)
python3 scripts/scrape_fares_trip_snapshot_range.py --start 2026-08-20 --end 2026-08-26

# trip.ferizy.com — single-day full-scale fare scraper (140 routes, HMAC-SHA512 AIFSignature, checkpointed)
python3 scripts/scrape_fares_trip_fullscale.py --date 2026-08-21

# Trip + Classic — one normalized all-portal CSV
python3 scripts/merge_all_ferizy_fares.py --start-date 2026-08-20 --end-date 2026-08-26

# Trip + Classic — one normalized route master
python3 scripts/merge_all_ferizy_routes.py

# trip.ferizy.com — public masters (needs no auth; AIFSignature via openssl AES-128-ECB)
python3 scrape_master.py                  # 65 origins → 140 routes (checkpointed)
python3 scrape_route_metadata_fast.py     # service_type + checkin per route (ThreadPool 2)
python3 scrape_public_parameters.py       # 19 params
python3 scrape_misc_public.py             # 22 extra public endpoints
python3 crawl_pages.py                    # 14 static pages

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
