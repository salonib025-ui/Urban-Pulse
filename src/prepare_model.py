
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent

INPUT_PATH = (
    ROOT / "data" / "processed" / "metro_traffic_cleaned.csv"
)

OUTPUT_PATH = (
    ROOT / "data" / "processed" / "metro_traffic_modeling.csv"
)


def main():
    print("=" * 60)
    print("URBAN PULSE - MODEL DATA PREPARATION")
    print("=" * 60)

    df = pd.read_csv(INPUT_PATH, parse_dates=["date_time"])

    original_rows = len(df)

    # Treat zero-Kelvin readings as invalid temperature measurements.
    invalid_temp = df["temp"] <= 0
    df.loc[invalid_temp, "temp"] = float("nan")
    df.loc[invalid_temp, "temp_celsius"] = float("nan")

    # Treat the extreme rainfall reading as missing for modelling.
    # Keep the original cleaned dataset unchanged.
    extreme_rain = df["rain_1h"] > 100
    df.loc[extreme_rain, "rain_1h"] = float("nan")

    # Sort chronologically for later time-based train/test splitting.
    df = df.sort_values("date_time").reset_index(drop=True)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)

    print(f"\nRows retained: {len(df)}")
    print(f"Rows removed: {original_rows - len(df)}")
    print(f"Invalid temperature measurements marked missing: {int(invalid_temp.sum())}")
    print(f"Extreme rainfall measurements marked missing: {int(extreme_rain.sum())}")
    print(f"Missing temperature values now: {int(df['temp_celsius'].isna().sum())}")
    print(f"Missing rainfall values now: {int(df['rain_1h'].isna().sum())}")
    print(f"Missing traffic targets: {int(df['traffic_volume'].isna().sum())}")

    print(f"\nSaved modelling dataset to:\n{OUTPUT_PATH}")
    print("\nModel data preparation completed.")


if __name__ == "__main__":
    main()