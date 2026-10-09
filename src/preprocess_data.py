
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent

INPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "metro_interstate_traffic_volume.csv"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "metro_traffic_cleaned.csv"
)


def main():
    print("=" * 60)
    print("       URBAN PULSE - DATA PREPROCESSING")
    print("=" * 60)

    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {INPUT_PATH}"
        )

    # 1. Load the original dataset
    df = pd.read_csv(INPUT_PATH)
    original_rows = len(df)

    print(f"\nOriginal rows: {original_rows}")

    # 2. Convert whitespace-only strings to missing values
    df = df.replace(r"^\s*$", pd.NA, regex=True)

    # 3. Remove exact duplicate rows
    duplicates = int(df.duplicated().sum())
    df = df.drop_duplicates().copy()

    print(f"Exact duplicate rows removed: {duplicates}")

    # 4. Parse timestamps using the verified format
    df["date_time"] = pd.to_datetime(
        df["date_time"],
        format="%d-%m-%Y %H:%M",
        errors="coerce"
    )

    invalid_dates = int(df["date_time"].isna().sum())

    if invalid_dates:
        print(f"Rows with invalid timestamps removed: {invalid_dates}")
        df = df.dropna(subset=["date_time"]).copy()

    # 5. Handle holiday entries
    # Preserve the distinction between named holidays and blanks.
    df["holiday"] = (
        df["holiday"]
        .fillna("No holiday recorded")
        .astype(str)
        .str.strip()
    )

    # 6. Convert temperature from Kelvin to Celsius
    df["temp_celsius"] = df["temp"] - 273.15

    # 7. Create time-based features
    df["hour"] = df["date_time"].dt.hour
    df["day_of_week"] = df["date_time"].dt.day_name()
    df["day_of_week_num"] = df["date_time"].dt.dayofweek
    df["month"] = df["date_time"].dt.month
    df["year"] = df["date_time"].dt.year
    df["is_weekend"] = (
        df["day_of_week_num"] >= 5
    ).astype(int)

    # 8. Sort chronologically
    df = df.sort_values("date_time").reset_index(drop=True)

    # 9. Create the output directory and save
    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    df.to_csv(OUTPUT_PATH, index=False)

    # 10. Print preprocessing report
    print("\nPREPROCESSING SUMMARY")
    print("-" * 40)
    print(f"Original rows: {original_rows}")
    print(f"Final rows: {len(df)}")
    print(f"Columns after feature engineering: {len(df.columns)}")
    print(f"Missing values remaining: {int(df.isna().sum().sum())}")
    print(f"Invalid timestamps remaining: {int(df['date_time'].isna().sum())}")
    print(f"Date range: {df['date_time'].min()} to {df['date_time'].max()}")

    print("\nNew features:")
    print(
        "temp_celsius, hour, day_of_week, "
        "day_of_week_num, month, year, is_weekend"
    )

    print(f"\nCleaned dataset saved to:\n{OUTPUT_PATH}")
    print("\nFirst five cleaned records:")
    print(df.head().to_string(index=False))

    print("\nPreprocessing completed successfully!")


if __name__ == "__main__":
    main()