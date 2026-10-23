# SCD2 / rollback: baseline gate

## AWS test evidence confirmed — 24 October 2026

User reports all tests passed and supplied final screenshots: attempts 9 (SUCCEEDED4 / NO_OP1 / FAILED4); ledger4 (fact_rows3,5,5,5); user versions 1=2,2=2,3=2,4=1, current1 for each. Late injected failure followed by successful retry is visible. This closes this synthetic suite, not concurrency/cancellation or production acceptance. Runtime defects found and repaired: assertion VARCHAR length, unsupported IF NOT EXISTS CTAS, and bare RAISE in atomic exception handler. Validation database still requires its separately prepared atomic-handler patch; not yet applied live.

## Fixture package prepared — 24 October 2026

User confirmed the empty installation in thelook_scd_test passed (etl4/stg7/dw5).
`outputs/aws/scd-test-fixtures-v1.zip` now contains 49 typed synthetic Parquet files, 49 manifests, upload verification script, package hashes, and ordered SQL for bootstrap/change/unchanged/replay/three invalid inputs/late injected failure/retry.
Builder: `code/build_scd_test_package.py`; local tests: `code/test_scd_test_package.py` (5 passed). No AWS execution performed by agent. Follow README_TH.md inside the archive. Preserve one SQL session for temporary snapshots and controls; expected failures run as separate CALLs in autocommit.
All regular tests use the installed loader unchanged. Late failure uses a renamed copy with a single explicit RAISE after fact insertion. Exact clone difference checked locally. It is never installed over etl.load_batch.

24 October 2026 (Asia/Bangkok). Raw and curated Catalog metadata checks passed. The next stage is warehouse behavior testing; these tests have NOT run on AWS yet.

## Run now

1. Resume thelook-redshift-cluster-1; wait for Available.
2. Open Query Editor v2 and explicitly select database thelook_glue_validation, not dev.
3. Open code/sql/08_scd_rollback_preflight.sql. Run the first SELECT alone. Continue only when database_check=PASS.
4. Execute the remaining SELECTs and save results. This file is read-only and does not call the loader.
5. Expected baseline: one SUCCEEDED ledger entry for batch 20261023T151247118967Z_f8a02155, users total/current 100000, products 29120, DC 10, fact 181759, all violations 0. Bootstrap users should have BOOTSTRAP_SNAPSHOT origin. Both sale_price totals must be 10827118.925100 and counts 181759.
6. If different, investigate the baseline before generating mutations. Do not reset/delete the working warehouse to make this check pass.

## Tests to prepare after baseline confirmation

Use a dedicated integration-test database and isolated S3 test prefix; preserve the successful validation database. The test harness must install the same generated loader and exercise COPY and load_batch, not a hand-rewritten SCD procedure. Prepare synthetic seven-table fixtures with internally consistent PK/FK, dates, flags, monetary controls and explicit synthetic observation timestamps.

| Scenario | Required result |
|---|---|
| Bootstrap | One current version per user; origin BOOTSTRAP_SNAPSHOT |
| Existing user attribute change | Close old version at new observation time; create one current version; unchanged users retain key/version |
| New user | One OBSERVED_NEW current row, valid_from NULL according to current design |
| City value → NULL and NULL → value | Null-safe change detection; consistent city_missing_token; history nonoverlapping |
| New batch with unchanged users | No extra user versions |
| Identical batch replay | NO_OP; data/ledger/checks unchanged, attempt audit increments |
| Duplicate PK / bad FK / money mismatch | Load fails; exact before/after comparisons of staging, dimensions, facts and ledger remain unchanged; FAILED audit exists |
| Failure after SCD writes | Test-only injection in isolated copy of loader, clearly labeled; verify rollback of user versions and facts, not only early validation failure |
| Successful retry after failed input | One atomic publish with consistent audit and no duplicate historical version |

Use exact table comparisons, not only equal counts/sums. Keep injected-procedure tests distinct from unmodified-loader tests in the report. Record the precise SQL/code hash used. No schedule until these tests pass; cancellation/concurrency testing remains a separate gate.

The baseline script does not complete SCD or rollback acceptance. Its results establish which data and procedure state are safe to use when preparing the isolated fixture package.
