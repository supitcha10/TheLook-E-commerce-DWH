# Contract before enabling new snapshots

Current working runner is intentionally locked to replay of an already published batch. Do not remove its guards to load a new snapshot.

## Required per-snapshot metadata

batch_id; immutable raw S3 prefix/file inventory and hashes; source_observed_at with timezone; evidence/owner for that time; extraction completeness (full snapshot); schema/rule version; processed_at; report and READY URI; approved package hash; explicit destination DB.

Never infer source_observed_at from S3 LastModified, Glue run time or maximum row created_at. Current source observation is unconfirmed, so new-snapshot SCD publication is blocked pending that information. Replay of the existing verified package remains permitted.

## Implementation sequence after metadata is supplied

1. Capture input metadata and an immutable source snapshot ID before starting Glue; persist Glue run ID.
2. Wait for Glue terminal state. FAILED/TIMEOUT/STOPPED stops downstream. SUCCEEDED alone does not authorize load.
3. Resolve this run's exact batch output, report and READY. Validate schema, all required checks, approved known-issue policy, quarantine and manifests. Verify source identity, part SHA256 and monetary controls.
4. Reject reused batch IDs with different identity; reject non-increasing observation time according to loader contract. Validate target DB and role. Do not silently substitute latest folder or new processing time.
5. Start a persistent Data API session. Populate seven input controls/five money controls, call atomic loader once, and verify ledger identity, reconciliations and audit. Use statement tokens and save statement IDs before polling.
6. On uncertain timeout do not automatically start a second SQL execution; inspect original statement and ledger first. On known failed attempt preserve audit and immutable artifacts, fix cause, then reviewed retry.
7. Add manual acceptance tests: invalid report/READY, changed part, wrong DB/batch, permissions failure, duplicate invocation, out-of-order snapshot and late-arriving facts. Only then add scheduler and agreed notification destination.

## Operational responsibility

DW owns schema/ETL/checks/loader and evidence. Source owner supplies observation metadata and business semantics. Infra supplies permitted runtime role, access, retention/cost alerts; BI confirms metrics and role-based access. No schedules, external messages, IAM grants or new paid resources are created by this document.

## Current remaining work

- New-snapshot orchestration and schedule: not implemented/deployed; blocked on trustworthy observation metadata and full-snapshot contract.
- Reporting views: installed and validated on AWS; see reporting acceptance report.
- BI dashboard/access: pending team/service permissions.
- Cancellation/concurrency/late-arriving acceptance and monitoring notification delivery: not certified by the synthetic SCD/replay tests.
