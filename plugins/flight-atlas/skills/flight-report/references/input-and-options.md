# Inputs and options

Preferred primary input is the detailed 19-column 小横 CSV. If missing, use [data-extraction.md](data-extraction.md) to guide export rather than substituting the APP XLS. XLS/XLSX reader support is retained for explicit legacy use; APP XLS is normally auxiliary corroboration only. Keep CSV as `--input` when both are supplied, preserve both sources, report conflicts and ask before any correction or addition. “Export mileage” then means the primary CSV's values, not silently the XLS mileage. There is no automatic CSV/XLS merge in the generator.

For conversational first use, run `scripts/preflight_report.py` before enrichment/rendering and use [first-run.md](first-run.md) to explain choices and resolve missing-data decisions. `distance_source: "export-then-tpm"` preserves supplied export mileage and uses city TPM only for missing cells; invalid populated cells remain errors. Fallback records retain individual sources and `fallback_reason`. User acceptance of queried values belongs to the conversational workflow, not an automatic CLI prompt.

Input: real BIFF `.xls`, ZIP `.xlsx` (even misnamed `.xls`), Excel 2003 XML, UTF-8 CSV/TSV. Formulas aren't executed; `.xlsx` formula fields need saved cached values. Unsupported HTML exports must be saved as `.xlsx` locally. Source bytes remain unchanged.

Updates may also use the private `flight-history.json` saved by FlightAtlas. A new small CSV is an increment only when the user asks to merge it into existing history. Use [incremental-update.md](incremental-update.md) and `scripts/merge_increment.py`; no automatic CSV/XLS merge is implied. Report generation saves source reporting values before enrichment/TPM conversion plus effective private config, enabling later updates without re-exporting old flights.

Required: flight number, departure, arrival; mileage in export mode. Recommended: date, codeshare flag, scheduled local departure/arrival, actual/scheduled duration, ICAO model, registration, MSN and first delivery date. Non-codeshare rows identify a missing airline from the flight prefix. Shared rows require a dated aircraft-operator and scheduled-route candidate accepted by the user; neither a marketing prefix nor current aircraft owner establishes the operator. OPEN placeholders and explicit unused/refunded/cancelled statuses are excluded with a warning; invalid/open ticket worksheets are skipped. Unknown/booked-only statuses should be reviewed in a private copy; other rows are treated as flown.

Recent CSV exports support the full 19-column schema: `日期,航班号,是否共享航班,出发机场,到达机场,表定出发,实际起飞,表定到达,实际降落,表定飞行时长,实际飞行时长,里程(公里),机型,注册号,舱位等级,座位号,含税票价,登机方式,下机方式`. Default total duration uses supplied actual duration (including `2小时30分`); only missing actual duration falls back to that row's scheduled duration with a separate audit. It does not reconstruct durations from clock fields. Slash-separated variants such as `330/343(X)` and `737/800(WL)` retain their source strings. A generic `DHC/8` does not establish Q400; a `PCF` descriptor is not dated lifecycle evidence. Cabin/seat/fare/boarding fields are discarded, not passed into reports.

Chinese headers and English canonical names are auto-detected. `column_map` maps canonical keys to exact header text, not column letters. Canonical keys: `date`, `flight`, `codeshare`, `departure`, `arrival`, `scheduled_departure`, `scheduled_arrival`, `departure_time`, `arrival_time`, `arrival_date`, `distance`, `registration`, `model`, `carrier`, `marketing`, `delivery`, `msn`, `minutes`, `scheduled_minutes`. ICAO field takes priority over a long descriptive type name. Other columns (tickets, passenger, remarks, arbitrary instructions) are discarded.

Config defaults:

```json
{
  "distance_source": "export",
  "include_repeated": true,
  "include_retired": false,
  "bar_min": 3,
  "route_min": 3,
  "repeat_min": 2,
  "name": "",
  "duration_policy": "actual-then-scheduled",
  "report_kind": "final",
  "png_scale": 1.5
}
```

First-run preflight proposes `place_of_birth` from the earliest flight's origin, `place_of_issue` from combined airport visits (alphabetical tie break), and `date_of_issue` from the earliest precise date; ask the user to confirm or replace all three. Partial dates are not expanded. `report_date` must be the current Codex client date for a new run; `valid_until` is forced to that date, including when an old config has another expiry. `age_as_of` defaults to that date. Store `identity_confirmed: true` after user confirmation. CLI derives defaults but does not provide conversational prompts.

`airport_bar_min` and `airline_bar_min` override shared `bar_min`. Airline singleton grid contains carriers below airline threshold; its caption adapts if these include 2+ flights. Airports below threshold remain in the word cloud. Command-line flags override matching config values. Boolean flags support `--no-include-repeated` / `--no-include-retired`. `--svg-only` skips final PNG conversion, but still needs Node/ECharts for the map. `--overwrite` permits replacing generated files in a nonempty output directory, not the input.

Duration policies: default `"actual-then-scheduled"` uses `表定飞行时长` only when actual duration is missing, separately audited. `"actual-only"` shows only the available actual sum, which may be incomplete. Neither reconstructs missing duration from clocks. Legacy `"complete"` is an explicit actual/clock/estimate workflow, not the default. Non-codeshare flags allow prefix identification; for legacy exports without the flag, enable `infer_airline_from_flight_number` and `flight_numbers_are_operating` only after user confirmation. Marked shared rows always override these switches and require `codeshare_resolutions`. `flight_prefix_airlines` extends the small seed; unknown codes remain unresolved. This seed is not a complete historical code-assignment registry.

For accepted `codeshare_resolutions`, dated `aircraft_details`, `logo_evidence` and photo rights metadata, follow [research-and-assets.md](research-and-assets.md). The candidate-preparation script never marks a result accepted. Formal generation stops on unresolved shared rows or missing required approved artwork; `report_kind: "diagnostic"` is only for non-final development previews.

Optional maps: `airport_aliases` maps Chinese/custom names to IATA. `airports` defines additional IATA records with `lat`, `lon`, `country` (ISO2), `tz` (IANA), `cn`. `airport_display_names` sets complete display names. `city_codes` supplies verified airport→TPM-city mapping. `carrier_aliases` maps verified alternate names to one operating-carrier name (never different codeshare operators); `airline_codes` maps that display name to its IATA code for logo selection. `logos` maps IATA airline codes to local SVG/PNG/JPEG; `alliance_logos` maps `star`, `skyteam`, `oneworld`. SVG may not contain scripts or external references. `signature_svg` is a local optional handwritten name image. Paths resolve relative to config; assets embed into SVG for offline viewing.

Supplemental records, all private/local:

```json
{
  "duration_estimates": [{"date":"2026-01-10","flight":"DEMO1","route":"PEK-XMN","minutes":170,"source":"verified timetable URL/date"}],
  "photos": [{"registration":"B-DEMO","msn":"DEMO-MSN","file":"aircraft.jpg","source":"photo page URL","credit":"photographer","license":"permission details"}],
  "aircraft_status": [{"registration":"B-DEMO","msn":"DEMO-MSN","checked_on":"2026-01-01","permanent_passenger_exit":true,"last_passenger_date":"2020 (year precision)","status":"converted to cargo","source":"verified history URL"}],
  "alliance_memberships": [{"carrier":"New airline name","alliance":"星空联盟","from":"2020-01-01","through":"2025-12-31","checked_on":"2026-01-01","source":"official membership URL"}]
}
```

Photo/status examples are synthetic, not assertions about real aircraft. A photo requires a matching MSN from the input; verify externally before filling. Reject conflicting MSNs or first-delivery dates. Card age means elapsed years since first delivery as of `age_as_of`, not manufacturing year. Lifecycle coverage is explicit; zero verified retirements doesn't imply all aircraft remain in passenger service.
