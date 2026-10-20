
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

    # 3. Parse timestamps
    df["date_time"] = pd.to_datetime(
        df["date_time"],
        format="%d-%m-%Y %H:%M",
        errors="coerce",
    )

    invalid_dates = int(df["date_time"].isna().sum())

    if invalid_dates:
        print(f"Invalid timestamps removed: {invalid_dates}")
        df = df.dropna(subset=["date_time"]).copy()

    # 4. Validate traffic volume and holiday consistency per timestamp
    for column in ["traffic_volume", "holiday"]:
        value_counts = (
            df.groupby("date_time")[column]
            .nunique(dropna=False)
        )

        conflicting_count = int((value_counts > 1).sum())

        if conflicting_count:
            raise ValueError(
                f"{conflicting_count} timestamps have conflicting "
                f"{column} values. Review the source data first."
            )

    # 5. Consolidate records sharing a timestamp.
    # Traffic and holiday are verified as consistent.
    # Numeric weather fields use the median.
    # Weather categories use the most frequent category;
    # alphabetical order breaks ties deterministically.
    numeric_weather = [
        "temp",
        "rain_1h",
        "snow_1h",
        "clouds_all",
    ]

    def most_common_category(series):
        values = series.dropna().astype(str)

        if values.empty:
            return pd.NA

        counts = values.value_counts()
        tied = counts[counts == counts.max()].index.tolist()

        return sorted(tied)[0]

    aggregations = {
        "traffic_volume": "first",
        "holiday": "first",
        "weather_main": most_common_category,
        "weather_description": most_common_category,
    }

    for column in numeric_weather:
        aggregations[column] = "median"

    before_consolidation = len(df)

    df = (
        df.groupby("date_time", as_index=False)
        .agg(aggregations)
        .sort_values("date_time")
        .reset_index(drop=True)
    )

    print("\nTIMESTAMP CONSOLIDATION")
    print("-" * 40)
    print(f"Rows before consolidation: {before_consolidation}")
    print(f"Unique timestamp rows: {len(df)}")
    print(
        "Rows consolidated: "
        f"{before_consolidation - len(df)}"
    )
    print(
        "Duplicate timestamps remaining: "
        f"{int(df['date_time'].duplicated().sum())}"
    )

    # 6. Handle holiday entries
    df["holiday"] = (
        df["holiday"]
        .fillna("No holiday recorded")
        .astype(str)
        .str.strip()
    )

    
    # 7. Handle invalid temperature values and convert to Celsius
    # Zero Kelvin is not a valid ordinary weather observation.
    invalid_temp = df["temp"].eq(0)

    print("\nTEMPERATURE QUALITY CHECK")
    print("-" * 40)
    print(f"Invalid zero-Kelvin records: {int(invalid_temp.sum())}")

    # Preserve the traffic records, but mark their temperatures as missing.
    df.loc[invalid_temp, "temp"] = float("nan")

    # Fill missing temperature values using nearby valid observations.
    df["temp"] = df["temp"].interpolate(
        method="linear",
        limit_direction="both",
    )

    # Convert the corrected Kelvin values to Celsius.
    df["temp_celsius"] = df["temp"] - 273.15


    # 8. Create time-based features
    df["hour"] = df["date_time"].dt.hour
    df["day_of_week"] = df["date_time"].dt.day_name()
    df["day_of_week_num"] = df["date_time"].dt.dayofweek
    df["month"] = df["date_time"].dt.month
    df["year"] = df["date_time"].dt.year
    df["is_weekend"] = (
        df["day_of_week_num"] >= 5
    ).astype(int)

    # 9. Standardize column order and sort chronologically
    column_order = [
        "holiday",
        "temp",
        "rain_1h",
        "snow_1h",
        "clouds_all",
        "weather_main",
        "weather_description",
        "date_time",
        "traffic_volume",
        "temp_celsius",
        "hour",
        "day_of_week",
        "day_of_week_num",
        "month",
        "year",
        "is_weekend",
    ]

    df = df[column_order]
    df = df.sort_values("date_time").reset_index(drop=True)

    # 10. Save the consolidated dataset
    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.to_csv(OUTPUT_PATH, index=False)

    # 11. Print preprocessing report
    print("\nPREPROCESSING SUMMARY")
    print("-" * 40)
    print(f"Original rows: {original_rows}")
    print(f"Final rows: {len(df)}")
    print(f"Columns after feature engineering: {len(df.columns)}")
    print(f"Missing values remaining: {int(df.isna().sum().sum())}")
    print(f"Invalid timestamps remaining: {int(df['date_time'].isna().sum())}")
    print(f"Unique timestamps: {df['date_time'].nunique()}")
    print(
        f"Date range: {df['date_time'].min()} "
        f"to {df['date_time'].max()}"
    )

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
