import csv
import io
import json
import urllib.request
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory


YEAR = 2025

BASE_URL = "https://" + "static.nhtsa.gov/odi/ffdd/cmpl/"
ZIP_URL = BASE_URL + "COMPLAINTS_RECEIVED_2025-2026.zip"

OUTPUT_FILE = Path(f"nhtsa_complaints_{YEAR}.jsonl")


# NHTSA CMPL.txt のフィールド定義
FIELDS = [
    "CMPLID",
    "ODINO",
    "MFR_NAME",
    "MAKETXT",
    "MODELTXT",
    "YEARTXT",
    "CRASH",
    "FAILDATE",
    "FIRE",
    "INJURED",
    "DEATHS",
    "COMPDESC",
    "CITY",
    "STATE",
    "VIN",
    "DATEA",
    "LDATE",
    "MILES",
    "OCCURENCES",
    "CDESCR",
    "CMPL_TYPE",
    "POLICE_RPT_YN",
    "PURCH_DT",
    "ORIG_OWNER_YN",
    "ANTI_BRAKES_YN",
    "CRUISE_CONT_YN",
    "NUM_CYLS",
    "DRIVE_TRAIN",
    "FUEL_SYS",
    "FUEL_TYPE",
    "TRANS_TYPE",
    "VEH_SPEED",
    "DOT",
    "TIRE_SIZE",
    "LOC_OF_TIRE",
    "TIRE_FAIL_TYPE",
    "ORIG_EQUIP_YN",
    "MANUF_DT",
    "SEAT_TYPE",
    "RESTRAINT_TYPE",
    "DEALER_NAME",
    "DEALER_TEL",
    "DEALER_CITY",
    "DEALER_STATE",
    "DEALER_ZIP",
    "PROD_TYPE",
    "REPAIRED_YN",
    "MEDICAL_ATTN",
    "VEHICLES_TOWED_YN",
    "STATE_OF_INCIDENT",
    "VEHICLE_OPERATOR",
]


def to_int(value):
    """Convert numeric string to int, or None."""
    value = value.strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def to_iso_date(value):
    """
    NHTSA YYYYMMDD -> YYYY-MM-DD
    Invalid/blank date -> None
    """
    value = value.strip()

    if len(value) != 8 or not value.isdigit():
        return None

    year = value[0:4]
    month = value[4:6]
    day = value[6:8]

    return f"{year}-{month}-{day}"


def make_document(row):
    """
    Convert NHTSA raw fields to a JSON document suitable for analysis.
    """

    raw = dict(zip(FIELDS, row))

    return {
        # Unique ID
        "id": raw["CMPLID"],

        # NHTSA reference number
        "odi_no_s": raw["ODINO"],

        # Vehicle
        "manufacturer_s": raw["MFR_NAME"],
        "make_s": raw["MAKETXT"],
        "model_s": raw["MODELTXT"],
        "model_year_i": to_int(raw["YEARTXT"]),

        # Incident
        "crash_s": raw["CRASH"],
        "incident_date": to_iso_date(raw["FAILDATE"]),
        "fire_s": raw["FIRE"],
        "injured_i": to_int(raw["INJURED"]),
        "deaths_i": to_int(raw["DEATHS"]),

        # Component
        "component_s": raw["COMPDESC"],

        # Location
        "state_s": raw["STATE"],
        "incident_state_s": raw["STATE_OF_INCIDENT"],

        # Dates
        "date_added": to_iso_date(raw["DATEA"]),
        "date": to_iso_date(raw["LDATE"]),

        # Failure information
        "miles_i": to_int(raw["MILES"]),
        "occurrences_i": to_int(raw["OCCURENCES"]),

        # Main complaint text
        "text": raw["CDESCR"],

        # Complaint metadata
        "complaint_type_s": raw["CMPL_TYPE"],
        "product_type_s": raw["PROD_TYPE"],

        # Additional safety information
        "police_report_s": raw["POLICE_RPT_YN"],
        "medical_attention_s": raw["MEDICAL_ATTN"],
        "vehicles_towed_s": raw["VEHICLES_TOWED_YN"],

        # Vehicle properties
        "fuel_type_s": raw["FUEL_TYPE"],
        "drive_train_s": raw["DRIVE_TRAIN"],
        "transmission_s": raw["TRANS_TYPE"],
        "vehicle_speed_i": to_int(raw["VEH_SPEED"]),
    }


def main():
    print(f"Downloading: COMPLAINTS_RECEIVED_2025-2026.zip")

    with TemporaryDirectory() as temp_dir:

        zip_path = Path(temp_dir) / "complaints.zip"

        # Download
        urllib.request.urlretrieve(ZIP_URL, zip_path)

        print(f"Downloaded: {zip_path.stat().st_size:,} bytes")

        count_total = 0
        count_selected = 0
        count_invalid = 0

        with zipfile.ZipFile(zip_path) as zf:

            # Find complaint data file inside ZIP
            candidates = [
                info
                for info in zf.infolist()
                if not info.is_dir()
                and info.filename.lower().endswith((".txt", ".lst"))
            ]

            if not candidates:
                raise RuntimeError("Complaint data file not found in ZIP")

            # Usually there is one main flat file.
            # If multiple exist, use the largest one.
            data_info = max(candidates, key=lambda x: x.file_size)

            print(f"Reading: {data_info.filename}")

            with zf.open(data_info) as raw_file, \
                    io.TextIOWrapper(
                        raw_file,
                        encoding="cp1252",
                        errors="replace",
                        newline=""
                    ) as text_file, \
                    OUTPUT_FILE.open(
                        "w",
                        encoding="utf-8",
                        newline="\n"
                    ) as output:

                reader = csv.reader(text_file, delimiter="\t")

                for row in reader:
                    count_total += 1

                    # Current NHTSA format has 51 fields.
                    if len(row) < len(FIELDS):
                        count_invalid += 1
                        continue

                    # LDATE = field 17 = index 16
                    ldate = row[16].strip()

                    # Received Date = 2025
                    if not ldate.startswith(str(YEAR)):
                        continue

                    document = make_document(row)

                    output.write(
                        json.dumps(
                            document,
                            ensure_ascii=False,
                            separators=(",", ":")
                        )
                    )
                    output.write("\n")

                    count_selected += 1

                    if count_selected % 10000 == 0:
                        print(f"Converted: {count_selected:,}")

        print()
        print("=== Completed ===")
        print(f"Input records : {count_total:,}")
        print(f"2025 records  : {count_selected:,}")
        print(f"Invalid rows  : {count_invalid:,}")
        print(f"Output        : {OUTPUT_FILE}")


if __name__ == "__main__":
    main()