import argparse
import csv
import json
import time
import urllib.error
import urllib.parse
import urllib.request

from collections import Counter
from datetime import date, datetime, timedelta

from pathlib import Path


ML_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = ML_DIR / "config" / "stations.json"
RAW_DIR = ML_DIR / "data" / "raw" / "climate_daily"
PROCESSED_DIR = ML_DIR / "data" / "processed" / "climate_daily"
REPORT_DIR = ML_DIR / "reports"

MEASUREMENT_FIELDS = [
    "MEAN_TEMPERATURE",
    "MIN_TEMPERATURE",
    "MAX_TEMPERATURE",
    "TOTAL_PRECIPITATION",
    "TOTAL_RAIN",
    "TOTAL_SNOW",
    "SNOW_ON_GROUND",
    "SPEED_MAX_GUST",
    "MIN_REL_HUMIDITY",
]


def parse_args():
    with CONFIG_PATH.open(encoding="utf-8") as file:
        config = json.load(file)

    station_ids = [str(s["id"]) for s in config["stations"]]

    parser = argparse.ArgumentParser(
        description="Download ECCC daily climate observations."
    )
    parser.add_argument(
        "--station-id",
        default=station_ids[0],
        choices=station_ids,
        help="Station ID from config/stations.json.",
    )
    parser.add_argument(
        "--start-date",
        default=config["start_date"],
        help="Inclusive start date (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--end-date",
        default=date.today().isoformat(),
        help="Inclusive end date (YYYY-MM-DD); defaults to today.",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=int(config.get("page_size", 1000)),
    )
    args = parser.parse_args()

    try:
        start = date.fromisoformat(args.start_date)
        end = date.fromisoformat(args.end_date)
    except ValueError as exc:
        parser.error(f"Invalid date: {exc}")

    if start > end:
        parser.error("--start-date must not be after --end-date.")
    if args.page_size < 1:
        parser.error("--page-size must be at least 1.")

    station = next(s for s in config["stations"]
                   if str(s["id"]) == args.station_id)
    return config, station, args


def fetch_json(url, attempts=4):
    for attempt in range(1, attempts + 1):
        try:
            request = urllib.request.Request(
                url,
                headers={"User-Agent": "ATMOSYNC-ML/1.0"}
            )
            with urllib.request.urlopen(request, timeout=45) as response:
                if response.status != 200:
                    raise RuntimeError(
                        f"Unexpected HTTP status: {response.status}"
                    )
                return json.loads(response.read().decode("utf-8"))

        except (
            urllib.error.URLError,
            TimeoutError,
            json.JSONDecodeError,
            RuntimeError,
        ) as exc:
            if attempt == attempts:
                raise RuntimeError(
                    f"Request failed after {attempts} attempts: {exc}"
                ) from exc
            wait_seconds = min(2 ** attempt, 16)
            print(
                f"Request attempt {attempt} failed: {exc}. "
                f"Retrying in {wait_seconds}s..."
            )
            time.sleep(wait_seconds)


def write_csv(path, records):
    # Use the union of fields so optional source fields are not discarded.
    field_names = sorted({key for row in records for key in row})
    if "ID" in field_names:
        field_names.remove("ID")
        field_names.insert(0, "ID")
    if "LOCAL_DATE" in field_names:
        field_names.remove("LOCAL_DATE")
        field_names.insert(1 if field_names and field_names[0] == "ID" else 0,
                           "LOCAL_DATE")

    with path.open("w", newline="", encoding="utf-8-sig") as file:
        if field_names:
            writer = csv.DictWriter(
                file, fieldnames=field_names, extrasaction="ignore"
            )
            writer.writeheader()
            writer.writerows(records)


def main():
    config, station, args = parse_args()
    api_url = config["api_base_url"]

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    raw_run_dir = RAW_DIR / str(station["id"]) / run_id
    raw_run_dir.mkdir(parents=True, exist_ok=False)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    start = date.fromisoformat(args.start_date)
    end = date.fromisoformat(args.end_date)

    print(f"Station: {station['name']} ({station['id']})")
    print(f"Date range: {start} to {end}")
    print(f"Page size: {args.page_size}")
    print("Downloading data...")

    # ---------------------------------------------------------
    # 1. Download all API pages and preserve raw responses.
    # ---------------------------------------------------------
    offset = 0
    page_number = 0
    all_records = []
    raw_page_paths = []

    while True:
        params = {
            "f": "json",
            "limit": args.page_size,
            "offset": offset,
            "CLIMATE_IDENTIFIER": str(station["id"]),
            "datetime": f"{start.isoformat()}/{end.isoformat()}",
        }

        url = api_url + "?" + urllib.parse.urlencode(params)
        payload = fetch_json(url)

        if payload.get("type") != "FeatureCollection":
            raise RuntimeError(
                "API response is not a GeoJSON FeatureCollection."
            )

        features = payload.get("features", [])

        raw_path = raw_run_dir / f"page_{page_number:05d}.json"

        with raw_path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False)

        raw_page_paths.append(
            str(raw_path.relative_to(ML_DIR))
        )

        page_records = []

        for feature in features:
            properties = feature.get("properties") or {}
            record = dict(properties)

            record["_GEOMETRY"] = json.dumps(
                feature.get("geometry"),
                ensure_ascii=False,
            )

            page_records.append(record)

        all_records.extend(page_records)

        print(
            f"Page {page_number + 1}: {len(features)} records "
            f"(offset {offset})"
        )

        # A short page means the result set has ended.
        if len(features) < args.page_size:
            break

        offset += len(features)
        page_number += 1

    # ---------------------------------------------------------
    # 2. Validate station IDs and dates.
    # ---------------------------------------------------------
    accepted = []
    rejected = []

    for record in all_records:
        station_id = str(
            record.get("CLIMATE_IDENTIFIER", "")
        )
        raw_date = str(
            record.get("LOCAL_DATE", "")
        )[:10]

        try:
            record_date = date.fromisoformat(raw_date)
        except ValueError:
            rejected.append(record)
            continue

        if (
            station_id == str(station["id"])
            and start <= record_date <= end
        ):
            accepted.append(record)
        else:
            rejected.append(record)

    # ---------------------------------------------------------
    # 3. Remove duplicate records.
    # ---------------------------------------------------------
    seen = set()
    unique_records = []
    duplicate_count = 0

    for record in accepted:
        key = record.get("ID") or (
            str(record.get("CLIMATE_IDENTIFIER", "")),
            str(record.get("LOCAL_DATE", ""))[:10],
        )

        if key in seen:
            duplicate_count += 1
            continue

        seen.add(key)
        unique_records.append(record)

    unique_records.sort(
        key=lambda row: str(row.get("LOCAL_DATE", ""))
    )

    # ---------------------------------------------------------
    # 4. Save the processed CSV.
    # ---------------------------------------------------------
    output_name = (
        f"station_{station['id']}_"
        f"{start.isoformat()}_{end.isoformat()}.csv"
    )

    csv_path = PROCESSED_DIR / output_name
    write_csv(csv_path, unique_records)

    # ---------------------------------------------------------
    # 5. Count missing measurements.
    # ---------------------------------------------------------
    missing_measurement_counts = {
        field: sum(
            1
            for row in unique_records
            if row.get(field) is None
            or str(row.get(field, "")).strip() == ""
        )
        for field in MEASUREMENT_FIELDS
    }

    # ---------------------------------------------------------
    # 6. Check calendar-date completeness.
    # ---------------------------------------------------------
    observed_dates = sorted({
        str(row.get("LOCAL_DATE", ""))[:10]
        for row in unique_records
        if row.get("LOCAL_DATE")
    })

    expected_dates = {
        (start + timedelta(days=day)).isoformat()
        for day in range((end - start).days + 1)
    }

    missing_dates = sorted(
        expected_dates - set(observed_dates)
    )


    # ---------------------------------------------------------
    # 7. Count non-empty source flags.
    # ---------------------------------------------------------
    available_fields = {
        key
        for row in unique_records
        for key in row
    }

    flag_fields = sorted(
        key
        for key in available_fields
        if key.endswith("_FLAG")
    )

    source_flag_counts = {}
    missing_source_flag_counts = {}

    for flag_field in flag_fields:
        non_empty_flags = [
            str(row[flag_field]).strip()
            for row in unique_records
            if row.get(flag_field) is not None
            and str(row.get(flag_field)).strip() != ""
        ]

        counts = Counter(non_empty_flags)

        source_flag_counts[flag_field] = dict(counts)

        missing_source_flag_counts[flag_field] = (
            len(unique_records) - len(non_empty_flags)
        )
    # ---------------------------------------------------------
    # 8. Build the ingestion report.
    # ---------------------------------------------------------
    report = {
        "status": (
            "success"
            if not rejected
            else "completed_with_rejected_records"
        ),
        "station_id": str(station["id"]),
        "station_name": station["name"],
        "api_base_url": api_url,
        "requested_start_date": start.isoformat(),
        "requested_end_date": end.isoformat(),
        "retrieved_records_before_deduplication": len(all_records),
        "accepted_records_before_deduplication": len(accepted),
        "unique_records": len(unique_records),
        "duplicate_records_removed": duplicate_count,
        "records_rejected_by_station_date_validation": len(rejected),
        "pages_downloaded": len(raw_page_paths),
        "observed_first_date": (
            observed_dates[0] if observed_dates else None
        ),
        "observed_last_date": (
            observed_dates[-1] if observed_dates else None
        ),
        "distinct_observed_dates": len(observed_dates),
        "expected_calendar_dates": len(expected_dates),
        "missing_calendar_dates_count": len(missing_dates),
        "missing_calendar_dates": missing_dates,
        "missing_measurement_counts": missing_measurement_counts,
        "source_flag_counts": source_flag_counts,
        "missing_source_flag_counts": missing_source_flag_counts,
        "raw_page_files": raw_page_paths,
        "processed_csv": str(csv_path.relative_to(ML_DIR)),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }

    report_path = (
        REPORT_DIR
        / f"ingestion_{station['id']}_{run_id}.json"
    )

    with report_path.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2, ensure_ascii=False)

    # ---------------------------------------------------------
    # 9. Print the ingestion summary.
    # ---------------------------------------------------------
    print("\nIngestion complete.")
    print(f"Unique records: {len(unique_records)}")
    print(f"Duplicates removed: {duplicate_count}")
    print(f"Rejected records: {len(rejected)}")
    print(
        f"Observed dates: {report['observed_first_date']} "
        f"to {report['observed_last_date']}"
    )
    print(f"Expected calendar dates: {len(expected_dates)}")
    print(f"Missing calendar dates: {len(missing_dates)}")
    print(f"Processed CSV: {csv_path}")
    print(f"Report: {report_path}")

    print("Missing measurement counts:")
    for field, count in missing_measurement_counts.items():
        print(f"  {field}: {count}")

    print("Non-empty source flag counts:")
    for field, counts in source_flag_counts.items():
        print(f"  {field}: {counts}")


if __name__ == "__main__":
    main()