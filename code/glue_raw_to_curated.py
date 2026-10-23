"""Standalone AWS Glue 4.0 Spark job. Paste this entire file into Glue Studio.

Reads the seven immutable CSVs, writes candidate Parquet plus quality reports.
Only a batch containing _READY.json has passed validation. No Redshift writes.
Schema and baseline below are embedded so no extra Python modules are needed.
"""
import hashlib
import json
import math
import re
import sys
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext

SCHEMA = json.loads(r'''{
  "version": "curated-v1",
  "rounding": "ROUND_HALF_UP",
  "tables": {
    "distribution_centers": {
      "primary_key": "id",
      "columns": [
        {
          "name": "id",
          "type": "BIGINT",
          "nullable": false
        },
        {
          "name": "name",
          "type": "VARCHAR(256)",
          "nullable": false
        },
        {
          "name": "latitude",
          "type": "DOUBLE PRECISION",
          "nullable": false
        },
        {
          "name": "longitude",
          "type": "DOUBLE PRECISION",
          "nullable": false
        }
      ]
    },
    "products": {
      "primary_key": "id",
      "columns": [
        {
          "name": "id",
          "type": "BIGINT",
          "nullable": false
        },
        {
          "name": "cost",
          "type": "DECIMAL(18,6)",
          "nullable": false
        },
        {
          "name": "category",
          "type": "VARCHAR(128)",
          "nullable": false
        },
        {
          "name": "name",
          "type": "VARCHAR(1024)",
          "nullable": true
        },
        {
          "name": "brand",
          "type": "VARCHAR(256)",
          "nullable": true
        },
        {
          "name": "retail_price",
          "type": "DECIMAL(18,6)",
          "nullable": false
        },
        {
          "name": "department",
          "type": "VARCHAR(32)",
          "nullable": false
        },
        {
          "name": "sku",
          "type": "VARCHAR(128)",
          "nullable": false
        },
        {
          "name": "distribution_center_id",
          "type": "BIGINT",
          "nullable": false
        }
      ]
    },
    "users": {
      "primary_key": "id",
      "columns": [
        {
          "name": "id",
          "type": "BIGINT",
          "nullable": false
        },
        {
          "name": "first_name",
          "type": "VARCHAR(256)",
          "nullable": false
        },
        {
          "name": "last_name",
          "type": "VARCHAR(256)",
          "nullable": false
        },
        {
          "name": "email",
          "type": "VARCHAR(512)",
          "nullable": false
        },
        {
          "name": "age",
          "type": "SMALLINT",
          "nullable": false
        },
        {
          "name": "gender",
          "type": "VARCHAR(32)",
          "nullable": false
        },
        {
          "name": "state",
          "type": "VARCHAR(256)",
          "nullable": false
        },
        {
          "name": "street_address",
          "type": "VARCHAR(2048)",
          "nullable": false
        },
        {
          "name": "postal_code",
          "type": "VARCHAR(32)",
          "nullable": false
        },
        {
          "name": "city",
          "type": "VARCHAR(256)",
          "nullable": false
        },
        {
          "name": "country",
          "type": "VARCHAR(128)",
          "nullable": false
        },
        {
          "name": "latitude",
          "type": "DOUBLE PRECISION",
          "nullable": false
        },
        {
          "name": "longitude",
          "type": "DOUBLE PRECISION",
          "nullable": false
        },
        {
          "name": "traffic_source",
          "type": "VARCHAR(64)",
          "nullable": false
        },
        {
          "name": "created_at",
          "type": "TIMESTAMPTZ",
          "nullable": false
        }
      ]
    },
    "orders": {
      "primary_key": "order_id",
      "columns": [
        {
          "name": "order_id",
          "type": "BIGINT",
          "nullable": false
        },
        {
          "name": "user_id",
          "type": "BIGINT",
          "nullable": false
        },
        {
          "name": "status",
          "type": "VARCHAR(32)",
          "nullable": false
        },
        {
          "name": "gender",
          "type": "VARCHAR(32)",
          "nullable": false
        },
        {
          "name": "created_at",
          "type": "TIMESTAMPTZ",
          "nullable": false
        },
        {
          "name": "returned_at",
          "type": "TIMESTAMPTZ",
          "nullable": true
        },
        {
          "name": "shipped_at",
          "type": "TIMESTAMPTZ",
          "nullable": true
        },
        {
          "name": "delivered_at",
          "type": "TIMESTAMPTZ",
          "nullable": true
        },
        {
          "name": "num_of_item",
          "type": "INTEGER",
          "nullable": false
        }
      ]
    },
    "order_items": {
      "primary_key": "id",
      "columns": [
        {
          "name": "id",
          "type": "BIGINT",
          "nullable": false
        },
        {
          "name": "order_id",
          "type": "BIGINT",
          "nullable": false
        },
        {
          "name": "user_id",
          "type": "BIGINT",
          "nullable": false
        },
        {
          "name": "product_id",
          "type": "BIGINT",
          "nullable": false
        },
        {
          "name": "inventory_item_id",
          "type": "BIGINT",
          "nullable": false
        },
        {
          "name": "status",
          "type": "VARCHAR(32)",
          "nullable": false
        },
        {
          "name": "created_at",
          "type": "TIMESTAMPTZ",
          "nullable": false
        },
        {
          "name": "shipped_at",
          "type": "TIMESTAMPTZ",
          "nullable": true
        },
        {
          "name": "delivered_at",
          "type": "TIMESTAMPTZ",
          "nullable": true
        },
        {
          "name": "returned_at",
          "type": "TIMESTAMPTZ",
          "nullable": true
        },
        {
          "name": "sale_price",
          "type": "DECIMAL(18,6)",
          "nullable": false
        }
      ]
    },
    "inventory_items": {
      "primary_key": "id",
      "columns": [
        {
          "name": "id",
          "type": "BIGINT",
          "nullable": false
        },
        {
          "name": "product_id",
          "type": "BIGINT",
          "nullable": false
        },
        {
          "name": "created_at",
          "type": "TIMESTAMPTZ",
          "nullable": false
        },
        {
          "name": "sold_at",
          "type": "TIMESTAMPTZ",
          "nullable": true
        },
        {
          "name": "cost",
          "type": "DECIMAL(18,6)",
          "nullable": false
        },
        {
          "name": "product_category",
          "type": "VARCHAR(128)",
          "nullable": false
        },
        {
          "name": "product_name",
          "type": "VARCHAR(1024)",
          "nullable": true
        },
        {
          "name": "product_brand",
          "type": "VARCHAR(256)",
          "nullable": true
        },
        {
          "name": "product_retail_price",
          "type": "DECIMAL(18,6)",
          "nullable": false
        },
        {
          "name": "product_department",
          "type": "VARCHAR(32)",
          "nullable": false
        },
        {
          "name": "product_sku",
          "type": "VARCHAR(128)",
          "nullable": false
        },
        {
          "name": "product_distribution_center_id",
          "type": "BIGINT",
          "nullable": false
        }
      ]
    },
    "events": {
      "primary_key": "id",
      "columns": [
        {
          "name": "id",
          "type": "BIGINT",
          "nullable": false
        },
        {
          "name": "user_id",
          "type": "BIGINT",
          "nullable": true
        },
        {
          "name": "sequence_number",
          "type": "INTEGER",
          "nullable": false
        },
        {
          "name": "session_id",
          "type": "VARCHAR(128)",
          "nullable": false
        },
        {
          "name": "created_at",
          "type": "TIMESTAMPTZ",
          "nullable": false
        },
        {
          "name": "ip_address",
          "type": "VARCHAR(64)",
          "nullable": false
        },
        {
          "name": "city",
          "type": "VARCHAR(256)",
          "nullable": false
        },
        {
          "name": "state",
          "type": "VARCHAR(256)",
          "nullable": false
        },
        {
          "name": "postal_code",
          "type": "VARCHAR(32)",
          "nullable": false
        },
        {
          "name": "browser",
          "type": "VARCHAR(128)",
          "nullable": false
        },
        {
          "name": "traffic_source",
          "type": "VARCHAR(64)",
          "nullable": false
        },
        {
          "name": "uri",
          "type": "VARCHAR(8192)",
          "nullable": false
        },
        {
          "name": "event_type",
          "type": "VARCHAR(64)",
          "nullable": false
        }
      ]
    }
  }
}''')
BASELINE = json.loads(r'''{
  "version": "provisional-v1",
  "recorded_on": "2026-10-18",
  "source_confirmation": "pending",
  "note": "Known issue counts belong only to this CSV snapshot. Do not refresh baseline automatically.",
  "tables": {
    "users": {
      "rows": 100000,
      "sha256": "7f03c981482f8ebabc88a47f9151d4591d0068325e5207d35e37aebb1d4e471f"
    },
    "events": {
      "rows": 2431963,
      "sha256": "8ac24f7be54edeefe0f212dab1d33c1e94ee6b0a315e310e2973aa8e4e837547"
    },
    "order_items": {
      "rows": 181759,
      "sha256": "fe86c46cb0b947cbcedc8abc066c4458b0b577de8d72e116d965476d3b143355"
    }
  },
  "issues": [
    {
      "id": "CITY-01-users",
      "table": "users",
      "rule": "null_like_text:city",
      "expected_count": 958,
      "expected_checked_rows": 100000
    },
    {
      "id": "CITY-01-events",
      "table": "events",
      "rule": "null_like_text:city",
      "expected_count": 23080,
      "expected_checked_rows": 2431963
    },
    {
      "id": "DATE-01-items",
      "table": "order_items",
      "rule": "date_order:shipped_at>=created_at",
      "expected_count": 35872,
      "expected_checked_rows": 118281
    }
  ]
}''')

RAW_ROOT = "s3://thelook-dwh-20241022/thelook/raw/initial-extract/"
OUTPUT_ROOT = "s3://thelook-dwh-20241022/thelook/curated/"
CONTROL_ROOT = "s3://thelook-dwh-20241022/thelook/control/"
QUARANTINE_ROOT = "s3://thelook-dwh-20241022/thelook/quarantine/"

RELATIONS = [
    ("products", "distribution_center_id", "distribution_centers", "id"),
    ("inventory_items", "product_id", "products", "id"),
    ("inventory_items", "product_distribution_center_id", "distribution_centers", "id"),
    ("orders", "user_id", "users", "id"),
    ("order_items", "order_id", "orders", "order_id"),
    ("order_items", "user_id", "users", "id"),
    ("order_items", "product_id", "products", "id"),
    ("order_items", "inventory_item_id", "inventory_items", "id"),
    ("events", "user_id", "users", "id"),
]


def convert_value(text, column):
    """Pure conversion, shared by the worker UDF and local boundary tests."""
    kind, name = column["type"], column["name"]
    missing = text is None or text.strip() == ""
    if missing:
        return None, None if column["nullable"] else name + ":required"
    trimmed = text.strip()
    try:
        if kind.startswith("VARCHAR"):
            limit = int(re.search(r"\d+", kind).group())
            if len(text.encode("utf-8")) > limit:
                raise ValueError("UTF8 length")
            return text, None
        if kind in ("BIGINT", "INTEGER", "SMALLINT"):
            if not re.fullmatch(r"[+-]?\d+(?:\.0+)?", trimmed):
                raise ValueError("integer syntax")
            value = int(trimmed.split(".")[0])
            bits = {"BIGINT": 64, "INTEGER": 32, "SMALLINT": 16}[kind]
            if not -(2 ** (bits - 1)) <= value < 2 ** (bits - 1):
                raise ValueError("integer range")
            if (name == "id" or name.endswith("_id") or name == "num_of_item") and value <= 0:
                raise ValueError("nonpositive identifier/count")
            return value, None
        if kind == "DOUBLE PRECISION":
            value = float(trimmed)
            if not math.isfinite(value):
                raise ValueError("nonfinite")
            if name in ("latitude", "longitude") and abs(value) > (90 if name == "latitude" else 180):
                raise ValueError("coordinate range")
            return value, None
        if kind == "DECIMAL(18,6)":
            with localcontext() as context:
                context.prec = 80
                value = Decimal(trimmed)
                if not value.is_finite():
                    raise ValueError("nonfinite decimal")
                rounded = value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
                if abs(rounded) >= Decimal("1000000000000"):
                    raise ValueError("decimal range")
            return rounded, None
        if kind == "TIMESTAMPTZ":
            if not re.search(r"(?:Z|[+-]\d{2}:?\d{2})$", trimmed, re.I):
                raise ValueError("timezone missing")
            fractional = re.search(r"[T ]\d{2}:\d{2}:\d{2}\.(\d+)", trimmed)
            if fractional and any(digit != "0" for digit in fractional.group(1)[6:]):
                raise ValueError("sub-microsecond timestamp")
            value = datetime.fromisoformat(re.sub(r"[zZ]$", "+00:00", trimmed))
            if value.tzinfo is None:
                raise ValueError("timezone missing")
            return value.astimezone(timezone.utc), None
        raise ValueError("unsupported type")
    except (ValueError, OverflowError, InvalidOperation):
        return None, name + ":invalid_type_or_range"


def convert_record(values, spec, name):
    data, reasons, money = {}, [], []
    for text, column in zip(values, spec["columns"]):
        key = column["name"]
        value, error = convert_value(text, column)
        data[key] = value
        if error:
            reasons.append(error)
        if column["type"] == "DECIMAL(18,6)":
            money.append((key, text.strip() if text and text.strip() else None,
                          str(value) if value is not None else None))
    if name in ("users", "events"):
        city = data["city"]
        flag = city is not None and city.strip().casefold() == "null"
        data["city_clean"] = None if flag else city
        data["city_missing_token"] = flag
    if name == "order_items":
        comparable = data["created_at"] is not None and data["shipped_at"] is not None
        data["item_dates_comparable"] = comparable
        data["item_shipped_before_created"] = (
            data["shipped_at"] < data["created_at"] if comparable else None
        )
    return data, reasons, money


def money_partition(rows):
    """Exact source/rounded decimal controls; no binary float aggregation."""
    with localcontext() as context:
        context.prec = 80
        totals = {}
        for row in rows:
            for key, source, target in row[0]:
                if source is None or target is None:
                    continue
                original, rounded = Decimal(source), Decimal(target)
                values = totals.setdefault(key, [Decimal(0)] * 4 + [0])
                values[0] += original
                values[1] += rounded
                values[2] += rounded - original
                values[3] += abs(rounded - original)
                values[4] += int(rounded != original)
        yield {key: [str(v) for v in values] for key, values in totals.items()}


def combine_money(partitions):
    names = ["source_accepted_sum", "expected_curated_sum", "rounding_delta",
             "sum_absolute_rounding", "rounded_rows"]
    result = {}
    with localcontext() as context:
        context.prec = 80
        for partition in partitions:
            for key, values in partition.items():
                target = result.setdefault(key, dict.fromkeys(names, Decimal(0)))
                for metric, value in zip(names, values):
                    target[metric] += Decimal(value)
    for metrics in result.values():
        metrics["rounded_rows"] = int(metrics["rounded_rows"])
    return result


def main():
    import boto3
    from awsglue.context import GlueContext
    from awsglue.job import Job
    from awsglue.utils import getResolvedOptions
    from pyspark import StorageLevel
    from pyspark.context import SparkContext
    from pyspark.sql import functions as F, types as T

    args = getResolvedOptions(sys.argv, ["JOB_NAME"])
    glue = GlueContext(SparkContext.getOrCreate())
    spark = glue.spark_session
    spark.conf.set("spark.sql.session.timeZone", "UTC")
    spark.conf.set("spark.sql.caseSensitive", "true")
    spark.conf.set("spark.sql.shuffle.partitions", "8")
    spark.conf.set("spark.sql.parquet.outputTimestampType", "TIMESTAMP_MICROS")
    spark.conf.set("spark.sql.csv.parser.columnPruning.enabled", "false")
    logger = glue.get_logger()
    job = Job(glue)
    job.init(args["JOB_NAME"], args)
    s3 = boto3.client("s3", region_name="us-east-1")
    batch = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "_" + uuid.uuid4().hex[:8]
    output, control, quarantine = [root + batch + "/" for root in (OUTPUT_ROOT, CONTROL_ROOT, QUARANTINE_ROOT)]
    report = {"batch_id": batch, "processed_at": datetime.now(timezone.utc).isoformat(),
              "source_observed_at": None, "source_root": RAW_ROOT,
              "schema_version": SCHEMA["version"], "rule_version": BASELINE["version"],
              "implementation": "glue-spark-v1", "source_confirmation": "pending",
              "status": "RUNNING", "output_root": output, "control_root": control,
              "tables": {}, "checks": [], "known_issues": []}

    def log(message):
        print(message, flush=True)
        logger.info(message)

    def split_uri(uri):
        return uri[5:].split("/", 1)

    def put_json(uri, obj):
        bucket, key = split_uri(uri)
        s3.put_object(Bucket=bucket, Key=key, ContentType="application/json",
                      Body=(json.dumps(obj, indent=2, ensure_ascii=False, default=str) + "\n").encode("utf-8"))

    def write_report():
        put_json(control + "validation_report.json", report)
        lines = ["# Glue raw-to-curated validation", "", "Batch: " + batch,
                 "Status: " + report["status"], "", "| Table | Raw | Curated | Quarantine |",
                 "|---|---:|---:|---:|"]
        for name, info in report["tables"].items():
            lines.append("| {} | {} | {} | {} |".format(name, info.get("raw_rows", "-"),
                         info.get("curated_rows", "-"), info.get("quarantined_rows", "-")))
        lines += ["", "| Check | Status | Detail |", "|---|---|---|"]
        for check in report["checks"]:
            lines.append("| {check} | {status} | {detail} |".format(**check))
        lines += ["", "Known issues remain pending source confirmation.",
                  "Use only batches with _READY.json. This job does not load Redshift."]
        bucket, key = split_uri(control + "validation_report.md")
        s3.put_object(Bucket=bucket, Key=key, ContentType="text/markdown; charset=utf-8",
                      Body=("\n".join(lines) + "\n").encode("utf-8"))

    def check(name, passed, detail):
        report["checks"].append({"check": name, "status": "PASS" if passed else "FAIL", "detail": str(detail)})

    def identity(metadata):
        return (metadata.get("VersionId"), metadata["ETag"], metadata["ContentLength"], metadata["LastModified"])

    types = {"BIGINT": T.LongType(), "INTEGER": T.IntegerType(), "SMALLINT": T.ShortType(),
             "DOUBLE PRECISION": T.DoubleType(), "TIMESTAMPTZ": T.TimestampType(),
             "DECIMAL(18,6)": T.DecimalType(18, 6)}

    def typed_schema(spec, name):
        # UDF fields nullable so rejected records can carry conversion failures.
        fields = [T.StructField(c["name"], T.StringType() if c["type"].startswith("VARCHAR") else types[c["type"]], True)
                  for c in spec["columns"]]
        if name in ("users", "events"):
            fields += [T.StructField("city_clean", T.StringType()), T.StructField("city_missing_token", T.BooleanType())]
        if name == "order_items":
            fields += [T.StructField("item_shipped_before_created", T.BooleanType()), T.StructField("item_dates_comparable", T.BooleanType())]
        return T.StructType(fields)

    tables = {}
    active = []
    log("RAW_TO_CURATED_START batch=" + batch)
    log("VALIDATION_REPORT=" + control + "validation_report.json")
    try:
        write_report()
        for name, spec in SCHEMA["tables"].items():
            log("READING_TABLE=" + name)
            uri = RAW_ROOT + name + ".csv"
            bucket, key = split_uri(uri)
            response = s3.get_object(Bucket=bucket, Key=key)
            source_identity = identity(response)
            digest = hashlib.sha256()
            body = response["Body"]
            try:
                for chunk in iter(lambda: body.read(1024 * 1024), b""):
                    digest.update(chunk)
            finally:
                body.close()
            info = {"source_uri": uri, "source_sha256": digest.hexdigest(),
                    "source_etag": response["ETag"], "source_version_id": response.get("VersionId"),
                    "source_bytes": response["ContentLength"], "parquet": output + name + "/"}
            report["tables"][name] = info
            raw_schema = T.StructType([T.StructField(c["name"], T.StringType()) for c in spec["columns"]])
            raw = (spark.read.schema(raw_schema).option("header", "true").option("enforceSchema", "false")
                   .option("encoding", "UTF-8").option("mode", "FAILFAST").option("multiLine", "true")
                   .option("quote", '"').option("escape", '"').option("nullValue", "\u0000")
                   .option("ignoreLeadingWhiteSpace", "false").option("ignoreTrailingWhiteSpace", "false")
                   .csv(uri).repartition(4))
            data_schema = typed_schema(spec, name)
            result_schema = T.StructType([
                T.StructField("data", data_schema),
                T.StructField("reasons", T.ArrayType(T.StringType())),
                T.StructField("money", T.ArrayType(T.StructType([
                    T.StructField("column", T.StringType()), T.StructField("source", T.StringType()),
                    T.StructField("rounded", T.StringType())])))])
            converter = F.udf(lambda row, spec=spec, name=name: convert_record(list(row), spec, name), result_schema)
            evaluated = raw.withColumn("_result", converter(F.struct(*raw.columns))).persist(StorageLevel.MEMORY_AND_DISK)
            active.append(evaluated)
            raw_count = evaluated.count()
            rejects = evaluated.filter(F.size("_result.reasons") > 0)
            rejected = rejects.count()
            info.update(raw_rows=raw_count, quarantined_rows=rejected, curated_rows=raw_count - rejected)
            if rejected:
                reject_path = quarantine + name + "/"
                rejects.select(*raw.columns, F.col("_result.reasons").alias("rejection_rules"),
                               F.lit(uri).alias("source_file")).write.mode("errorifexists").json(reject_path)
                info["quarantine"] = reject_path
            accepted = evaluated.filter(F.size("_result.reasons") == 0)
            converted = accepted.select("_result.data.*")
            money_columns = [c["name"] for c in spec["columns"] if c["type"] == "DECIMAL(18,6)"]
            info["money"] = combine_money(accepted.select("_result.money").rdd.mapPartitions(money_partition).collect()) if money_columns else {}
            converted.write.mode("errorifexists").option("compression", "snappy").parquet(info["parquet"])
            readback = spark.read.parquet(info["parquet"])
            read_count = readback.count()
            check(name + ":nonempty", raw_count > 0, raw_count)
            check(name + ":row_reconciliation", raw_count == read_count + rejected, f"raw={raw_count}, readback={read_count}, quarantine={rejected}")
            check(name + ":no_rejected_rows", rejected == 0, rejected)
            check(name + ":schema_readback", [(f.name, f.dataType) for f in readback.schema] == [(f.name, f.dataType) for f in data_schema], "column order and logical data types")
            # SPARK-39612: exceptAll().count() can fail on Spark 3.3.0.
            # Group actual typed rows (not hashes), with opposite weights, to
            # compare multisets including duplicate multiplicity and NULLs.
            expected_rows = converted.select(
                F.struct(*converted.columns).alias("_row"), F.lit(1).alias("_weight")
            )
            actual_rows = readback.select(
                F.struct(*converted.columns).alias("_row"), F.lit(-1).alias("_weight")
            )
            differences = (expected_rows.unionByName(actual_rows).groupBy("_row")
                           .agg(F.sum("_weight").alias("_balance"))
                           .filter(F.col("_balance") != 0))
            equal = len(differences.take(1)) == 0
            check(name + ":typed_values_readback", equal, "exact typed multiset equality")
            if money_columns:
                sums = readback.agg(*[F.sum(c).alias(c) for c in money_columns]).first().asDict()
                for column in money_columns:
                    metrics = info["money"].setdefault(column, {"source_accepted_sum": Decimal(0), "expected_curated_sum": Decimal(0), "rounding_delta": Decimal(0)})
                    total = sums[column] if sums[column] is not None else Decimal(0)
                    metrics["readback_sum"] = total
                    with localcontext() as context:
                        context.prec = 80
                        valid = total == metrics["expected_curated_sum"] and total - metrics["source_accepted_sum"] == metrics["rounding_delta"]
                    check(name + "." + column + ":amount_reconciliation", valid, "exact Decimal totals and rounding delta")
            check(name + ":source_unchanged", source_identity == identity(s3.head_object(Bucket=bucket, Key=key)), "S3 version/ETag/length/last-modified before and after reading")
            tables[name] = readback
            evaluated.unpersist()
            active.remove(evaluated)
            log(f"TABLE_COMPLETE {name}: raw={raw_count}, curated={read_count}, quarantine={rejected}")
            write_report()

        for name, spec in SCHEMA["tables"].items():
            pk = spec["primary_key"]
            duplicate = tables[name].groupBy(pk).count().filter(F.col(pk).isNull() | (F.col("count") > 1)).count()
            check(name + ":primary_key", duplicate == 0, f"null/duplicate key groups={duplicate}")
        for child, fk, parent, pk in RELATIONS:
            orphan = tables[child].filter(F.col(fk).isNotNull()).join(tables[parent].select(F.col(pk).alias(fk)).distinct(), fk, "left_anti").count()
            check(child + "." + fk + ":foreign_key", orphan == 0, f"orphan rows={orphan}")
        items, orders, inventory = tables["order_items"], tables["orders"], tables["inventory_items"]
        counts = items.groupBy("order_id").count()
        mismatch = orders.join(counts, "order_id", "left").filter(F.col("num_of_item") != F.coalesce(F.col("count"), F.lit(0))).count()
        check("orders:item_counts", mismatch == 0, mismatch)
        for parent, pk, fk, field in [(orders, "order_id", "order_id", "user_id"), (inventory, "id", "inventory_item_id", "product_id")]:
            lookup = parent.select(F.col(pk).alias("_pk"), F.col(field).alias("_value"))
            mismatch = items.join(lookup, items[fk] == lookup["_pk"], "left").filter(~F.col(field).eqNullSafe(F.col("_value"))).count()
            check("order_items:" + field + "_matches_parent", mismatch == 0, mismatch)

        for issue in BASELINE["issues"]:
            name = issue["table"]
            flag = "item_shipped_before_created" if name == "order_items" else "city_missing_token"
            result = tables[name].agg(F.sum(F.when(F.col(flag), 1).otherwise(0)).alias("actual"), F.count(flag).alias("denominator")).first()
            actual, denominator = result["actual"] or 0, result["denominator"]
            info, expected = report["tables"][name], BASELINE["tables"][name]
            same = (actual == issue["expected_count"] and denominator == issue["expected_checked_rows"]
                    and info["source_sha256"] == expected["sha256"] and info["raw_rows"] == expected["rows"])
            report["known_issues"].append({"issue_id": issue["id"], "status": "KNOWN_ISSUE" if same else "WARN",
                "actual_rows": actual, "expected_rows": issue["expected_count"], "comparable_rows": denominator,
                "source_confirmation": "pending"})
        report["status"] = ("FAIL" if any(c["status"] == "FAIL" for c in report["checks"]) else
                            "REVIEW_REQUIRED" if any(i["status"] == "WARN" for i in report["known_issues"]) else "PASS_WITH_KNOWN_ISSUES")
        write_report()
        if report["status"] != "PASS_WITH_KNOWN_ISSUES":
            raise RuntimeError("Validation requires review: " + report["status"] + "; " + control + "validation_report.json")
        job.commit()
        put_json(output + "_READY.json", {"batch_id": batch, "status": report["status"],
                 "validation_report": control + "validation_report.json", "source_observed_at": None})
        log("RAW_TO_CURATED_PASSED batch=" + batch)
        log("CURATED_OUTPUT=" + output)
    except Exception as exc:
        if report["status"] not in ("FAIL", "REVIEW_REQUIRED"):
            report["status"] = "FAILED_INCOMPLETE"
        # Exception text from Spark may include raw personal data; keep it out of the report.
        report["error_type"] = type(exc).__name__
        try:
            write_report()
        except Exception:
            log("REPORT_WRITE_FAILED: inspect the job failure in CloudWatch")
        raise
    finally:
        for frame in active:
            frame.unpersist()


if __name__ == "__main__":
    main()
