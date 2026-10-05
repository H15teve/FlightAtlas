# Distance and aircraft evidence

## Mileage

Export mode retains the user's kilometre basis, rounded to an integer; it does not calculate airport geographic distance. TPM mode uses **cities** and converts international statute miles by 1.609344, round-half-up per segment. PEK/PKX→BJS, TFU→CTU, XIY→SIA, HND/NRT→TYO, JFK/EWR/LGA→NYC, etc. Config mappings extend these, but don't substitute a capital for a city merely because its code is convenient.

The free [JAL sector mileage calculator](https://www121.jal.co.jp/JmbWeb/JR/SectionMile_en.do) states an IATA TPM basis and accepts city codes. This is a free third-party calculator, **not** a licensed copy of IATA Mileage Online/TPM Manual. Its current revision is not a historical flight-date edition. Do not bypass access controls, CAPTCHA, throttling or terms; stop on service errors. Query only missing unique city pairs, slowly, explicitly opt in, and cache evidence. Award-program mileage, routing flown and geographic distance are different concepts.

TPM cache shape:

```json
{"records":{"AAA-BBB":{"tpm_miles":1000,"basis":"IATA TPM","source":"verified reference URL","queried_on":"2026-10-04","edition":"verified revision or not disclosed"}}}
```

The city pair and number above are **synthetic format examples**; don't copy them as a verified lookup. Online queries include returned city names and response SHA256. Missing, invalid or non-TPM cache values block generation. Existing cache is reused until the user chooses a new cache/refresh; check query dates before publishing. Opposite directions share lookup mileage but remain separate flight-count routes.

## Aircraft identity/lifecycle

Registration alone is not a lifetime identifier. Confirm manufacturer serial number/MSN and the flight date before reusing delivery/operator/status data. Flight-date operating carrier comes from actual operation, not today's owner or a marketing flight prefix.

Sources in order: manufacturer/operator official fleet and delivery notices; regulator/registration registry; credible aircraft-history references and contemporaneous photos. Jetphotos aircraft/photo metadata can corroborate model, serial and dates, but a photo timestamp is not first delivery and missing pictures isn't retirement. Explicit delivery precision must be retained; don't expand a year/month into an invented day. Scheduled duration estimates must retain source and lookup date. Cross-check codeshares with operator timetable/boarding pass or a dated official record.

Retired section means **permanent exit from passenger service** (including verified freighter conversion), not necessarily scrapped. Storage, inactivity or missing ADS-B is not enough. Record evidence source, verification date, precise/qualified exit date and present status. Unknown remains unknown and is counted in coverage.

Photos stay local and require user rights/permission. Downloading a Jetphotos picture does not grant redistribution rights. Don't strip embedded photographer watermarks, logos or metadata. The renderer embeds supplied art; resulting reports are private unless the user approves publication and associated rights.

Alliance data is a dated seed, not a complete live airline database. Use actual flight date and full-membership intervals; unknown carriers and flights after the seed's verification date remain `归属待核验` until refreshed with a covering `checked_on` date. New membership rules must come from official alliance/airline sources. Never classify a partnership/codeshare as alliance membership.
