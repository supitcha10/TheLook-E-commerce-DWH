"""CloudShell: explicit create/start/status; plan is offline. Never updates existing resources."""
import argparse
import json
from pathlib import Path

REGION = "us-east-1"
ACCOUNT = "006816724683"
ROLE = f"arn:aws:iam::{ACCOUNT}:role/LabRole"
BUCKET = "thelook-dwh-20241022"
BATCH = "20261023T151247118967Z_f8a02155"
TABLES = ["distribution_centers", "products", "users", "orders", "order_items", "inventory_items", "events"]
CLASSIFIER = "thelook-csv-header-present"
CSV = {"Name": CLASSIFIER, "Delimiter": ",", "QuoteSymbol": '"', "ContainsHeader": "PRESENT"}


def spec(layer):
    root = f"s3://{BUCKET}/thelook/"
    paths = ([root + f"raw/initial-extract/{t}.csv" for t in TABLES] if layer == "raw"
             else [root + f"curated/{BATCH}/{t}/" for t in TABLES])
    return {
        "Name": f"thelook-{layer}-crawler", "Role": ROLE,
        "DatabaseName": f"thelook_{layer}",
        "Targets": {"S3Targets": [{"Path": p, "Exclusions": ["**/_*", "**/.*"]} for p in paths]},
        "Classifiers": [CLASSIFIER] if layer == "raw" else [],
        "SchemaChangePolicy": {"UpdateBehavior": "LOG", "DeleteBehavior": "LOG"},
        "RecrawlPolicy": {"RecrawlBehavior": "CRAWL_EVERYTHING"},
        "Configuration": json.dumps({"Version": 1.0, "Grouping": {"TableGroupingPolicy": "CombineCompatibleSchemas"}}),
    }


def subset(actual, expected):
    if isinstance(expected, dict):
        return all(k in actual and subset(actual[k], v) for k, v in expected.items())
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(subset(a, e) for a, e in zip(actual, expected))
    return actual == expected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["plan", "create", "start", "status"])
    parser.add_argument("layer", choices=["raw", "curated"])
    args = parser.parse_args()
    expected = spec(args.layer)
    if args.action == "plan":
        print(json.dumps(expected, indent=2))
        return
    import boto3
    session = boto3.Session(region_name=REGION)
    identity = session.client("sts").get_caller_identity()
    if identity["Account"] != ACCOUNT:
        raise RuntimeError("Wrong AWS account; no changes made")
    glue = session.client("glue")
    if args.action == "create":
        # Inspect potential conflicts before creating anything.
        try:
            existing = glue.get_crawler(Name=expected["Name"])["Crawler"]
        except glue.exceptions.EntityNotFoundException:
            existing = None
        if existing:
            observed = dict(existing)
            observed["Configuration"] = json.loads(observed.get("Configuration", "{}"))
            check = dict(expected)
            check["Configuration"] = json.loads(check["Configuration"])
            if observed.get("Role") == "LabRole":
                observed["Role"] = ROLE
            if not subset(observed, check):
                raise RuntimeError("Existing crawler configuration differs; inspect it manually. Nothing updated.")
        classifier_exists = False
        if args.layer == "raw":
            try:
                current = glue.get_classifier(Name=CLASSIFIER)["Classifier"]["CsvClassifier"]
                if not subset(current, CSV):
                    raise RuntimeError("Existing classifier differs; nothing updated")
                classifier_exists = True
            except glue.exceptions.EntityNotFoundException:
                pass
        try:
            glue.get_database(Name=expected["DatabaseName"])
        except glue.exceptions.EntityNotFoundException:
            glue.create_database(DatabaseInput={"Name": expected["DatabaseName"], "Description": "TheLook catalog; metadata only, schema contract remains in ETL code"})
        if args.layer == "raw" and not classifier_exists:
            glue.create_classifier(CsvClassifier=CSV)
        if not existing:
            glue.create_crawler(**expected)
        print("Configured:", expected["Name"], "(no schedule; not started)")
    elif args.action == "start":
        crawler = glue.get_crawler(Name=expected["Name"])["Crawler"]
        if crawler["State"] != "READY":
            raise RuntimeError("Crawler is already running/stopping; use status")
        # Never start a differently targeted crawler under the same name.
        for key in ("DatabaseName", "Targets", "Classifiers"):
            if not subset(crawler.get(key, []), expected[key]):
                raise RuntimeError(f"Crawler {key} differs from plan; not started")
        glue.start_crawler(Name=expected["Name"])
        print("Started:", expected["Name"], "Use status to check completion.")
    else:
        crawler = glue.get_crawler(Name=expected["Name"])["Crawler"]
        tables = []
        for page in glue.get_paginator("get_tables").paginate(DatabaseName=expected["DatabaseName"]):
            for table in page["TableList"]:
                sd = table.get("StorageDescriptor", {})
                tables.append({"name": table["Name"], "location": sd.get("Location"), "columns": sd.get("Columns", []), "partition_keys": table.get("PartitionKeys", []), "classification": table.get("Parameters", {}).get("classification")})
        report = {"crawler": expected["Name"], "state": crawler["State"], "last_crawl": crawler.get("LastCrawl"), "table_count": len(tables), "tables": tables}
        output = json.dumps(report, indent=2, default=str)
        Path(f"catalog_{args.layer}_status.json").write_text(output, encoding="utf-8")
        print(output)
        print("Metadata listing only: SUCCEEDED/7 tables still require location and schema review.")


if __name__ == "__main__":
    main()
