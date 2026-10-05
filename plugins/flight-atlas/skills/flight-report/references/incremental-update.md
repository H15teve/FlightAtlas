# Incremental updates

Use this workflow when a returning user provides only new flights. Do not treat
an increment as the user's entire history or add headline totals from two reports.
Recompute both reports from the merged flight records.

## Export only the requested range

Confirm the start/end dates. Replace only the first sentence of
[extraction-prompt.txt](extraction-prompt.txt), keeping every subsequent byte
unchanged. For example:

> 请导出我在2026年10月1日至2026年10月31日（按出发机场当地出发日期，含起止日期）乘坐过的全部航班，后文的“全部历史行程”和“全量”均仅指此范围，输出为【逗号分隔CSV】，可直接复制保存为 .csv。

`scripts/make_increment_prompt.py --from START --through END --output NEW_TXT`
creates this variant. The first sentence scopes the later unchanged “全部历史行程”
requirements. Validate that returned records are actually flown and within the
chosen inclusive departure-local date range. Counts are for this increment, not
the user's lifetime count. Date-boundary overlap with the prior export is allowed.

## Find the user's existing local history

Successful reports now include private `flight-history.json` and
`report-config.json`. Use the latest user-designated history/config, not the
template creator's or another user's data. The history stores whitelisted source
reporting values before carrier/aircraft enrichment or TPM conversion, so choosing
export mileage later does not reuse converted TPM as an export value. Confirmed
enrichment, assets and settings remain in the private config.
Keep the local logo/photo/signature files and TPM cache referenced by that config
available; copying only the two JSON files does not copy those assets.

If a previous report predates these files, ask for its full primary CSV and
confirmed config. A previous PNG or aggregate audit is not enough to reconstruct
history. Auxiliary APP XLS is still corroboration, not a second flight set.

## Merge and review

Run from the plugin root, with actual absolute private paths and the client date:

```sh
python scripts/merge_increment.py --history PREVIOUS_HISTORY --input NEW_CSV --config PREVIOUS_CONFIG --report-date YYYY-MM-DD --output NEW_MERGE_DIRECTORY
```

History may be the saved JSON or the previous full CSV. Both inputs are read-only.
The output directory must be new/empty and cannot contain an input/config file.
The CLI does not automatically inherit config: pass the previous config explicitly.
Missing config requires asking the user to select settings again, not claiming
that old settings were preserved.

Match normalized departure date + original exported flight number + actual
departure/arrival airport codes. Keep leading zeroes; do not collapse airports to
TPM cities. Exact duplicate imports do not add flights. Multiple same-key records
need scheduled departure evidence or user disambiguation. Missing/partial dates
in an incoming increment need clarification. Ambiguous identities and changes to
existing nonblank values or additions to blanks require user review; incoming
blanks never erase existing values.

Exit 2 with `status:needs-review` writes only `increment-audit.json`, not an
adoptable merged history. Show the actual candidate records and field differences.
Only after the human decides, create a private resolutions file:

```json
{"decisions":[{"id":"ID_FROM_AUDIT","action":"keep-existing","existing_index":0,"user_verified":true}]}
```

Actions: `keep-existing` keeps the selected candidate; `take-incoming` applies
the incoming nonmissing fields to it; `add-new` is only for a user-confirmed
distinct flight. `existing_index` is required for ambiguous candidates. IDs bind
the compared records; changed/stale decisions are rejected. Rerun with
`--resolutions DECISIONS` into another new directory. Retain the audit including
both conflicting values. Never infer permission to overwrite from the existence
of a newer export.

## Regenerate

With no pending issues, outputs are `flight-history.json`, `report-config.json`
and `increment-audit.json`. Show previous/incoming/added/duplicate/merged counts.
Existing flights absent from the increment remain present. Reimporting the same
increment must not increase totals.

Use merged history as `--input` and merged config as `--config` for preflight and
generation. Do not render only the new CSV. Preserve confirmed passport fields,
signature, thresholds, mileage policy, authorized local assets and enrichment.
Refresh report date, Valid until and age-as-of to the client date. Ask only for new
missing fields/assets/shared-flight verification or settings the user changes.
Changed shared-flight identity fields invalidate old confirmations. Refresh
time-sensitive aircraft lifecycle evidence when needed; permanent exits do not
need to be undone merely because an aircraft is absent from ADS-B.

After success verify merged flight count, visits = 2×merged flights, mileage and
duration across the complete history, and original input hashes. Deliver the new
report directory with its merge audit, and keep the previous history/report recoverable. These history,
config and audit files contain personal travel information: keep them private and
never package/publish them.
