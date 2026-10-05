# First-time choices and missing-data decisions

Before asking report options, locate the preferred detailed 小横 CSV. If none is supplied, use [data-extraction.md](data-extraction.md) and give the complete [extraction-prompt.txt](extraction-prompt.txt), APP entry path and continuation/saving instructions; wait for the user's data. APP-exported XLS is optional corroboration, not implicit permission to merge or replace the CSV. Only-XLS input needs a user choice to proceed with limited legacy coverage. Do not claim the plugin can retrieve the user's APP history directly.

Describe the two outputs before asking: a passport-style summary with world routes, distance, duration, airport/carrier counts; an atlas with aircraft, carriers/alliances, domestic routes and flight-number TOP3, airport bars/word cloud, and optional aircraft cards. Explain that ordinary exports usually cannot populate every aircraft section without enrichment.

## Report options

Offer a few plain-language choices together, not a list of unexplained flags. Include consequence and prerequisites:

- Mileage: **original export** uses the app's kilometre values and can run offline. **City TPM** replaces all distances with a common city-pair basis (PEK/PKX share Beijing), which can differ from airport-to-airport distance; requires sourced cache or authorized online queries. **Original first, TPM only if missing** preserves all supplied values and fills only blank mileage cells; the total has mixed source bases, documented per segment. Invalid populated values are reported, not silently replaced. The free JAL calculator is not the paid IATA product or a guaranteed historical edition. Present fallback query results for acceptance before applying them.
- **Repeated aircraft** shows which exact registrations were flown at least twice, plus counts, airline/type and available age. Requires registration; delivery date enables age. The most-flown aircraft has a photo card, which requires an identified, approved usable photo. This is separate from frequency of aircraft models and flight numbers.
- **Exited passenger service** shows previously flown aircraft confirmed to have permanently left passenger service, including verified cargo conversions. Requires registration + MSN and dated lifecycle evidence. Enabling it authorizes a requested section, not research or downloads. Parking or missing ADS-B does not establish retirement. No known entries means unresolved coverage, not "none retired".
- **Frequency threshold** is the minimum count displayed in airline bars, combined departure+arrival airport bars, and directed route rankings. At ≥4, airline bars require four flights, airport bars four combined visits, and route lists four flights in that direction. Reverse routes stay separate. Every airport remains in the word cloud; low-count airlines remain below the bars. Repeated-aircraft cards default to two rides independently; flight-number TOP3 is independent of these thresholds. Users may choose separate thresholds for each chart.

After preflight, explicitly show and ask the user to confirm/change these fields: Place of birth defaults to the earliest flight's departure airport; Place of issue defaults to the highest departure+arrival count airport (alphabetical tie, user can change); Date of issue defaults to the earliest flight's precise date. Valid until is the current **client** date, passed in config as `report_date`, not an old template expiry. These are report design fields, not an assertion about biological birthplace. Unknown/partial first-flight dates require user input, not an invented day. Signature is optional and blank by default. Never insert the template author's name/airports/date. Explicit prior answers do not need asking again.

Explain that the default duration sums provided actual duration and substitutes the same row's scheduled duration only for missing actual values; those substitutions are recorded separately. Shared-flight rows need a verified main number/operator before statistics; non-shared rows identify airlines from the flight prefix. Read [research-and-assets.md](research-and-assets.md) for matching and asset acquisition. Real logos and required photos are prerequisites for a finished report; a diagnostic preview with placeholders is not an alternative silently selected by the agent.

## Preflight and enrichment

Run the read-only preflight and summarize only relevant field counts, the selected worksheet/flight count, and missing-duration segments. Do not dump passenger/ticket data. Assess missing fields against selected sections rather than asking about every optional column indiscriminately.

For each material gap, explain the result if left unresolved and offer:

1. User supplies verified values or APP/boarding-pass screenshots (no account credentials required).
2. Agent researches authorized public sources, presents candidates with source/date/confidence, and user accepts/selects them. For a large history, agree on an initial batch and stop if historical coverage is inadequate. Do not imply exact old registrations can always be recovered from a flight number.
3. Leave unresolved and generate only what the data supports. Mark unknowns as unknown; do not fabricate aircraft, complete duration or retirement results.

After a registration is accepted, it can support model/MSN/delivery research. Confirm the registration's historical date identity, not just its current operator. Actual codeshare carrier needs dated flight evidence; original airline is an unverified fallback, not proof of operator. For missing flight duration, distinguish sourced timetable estimates from historical actual times.

Store confirmed user options and accepted enrichment in private config/sidecars; do not overwrite the export. Summarize configuration, remaining unknowns and any estimated durations before final generation. A CLI invocation can remain noninteractive for automation; the Codex skill supplies the conversational onboarding and acceptance gates.
