
import pandas as pd
from pathlib import Path

DATA_PATH = Path("data/raw/metro_interstate_traffic_volume.csv")

df = pd.read_csv(DATA_PATH)

print("\n" + "=" * 60)
print("TEMPERATURE ANOMALIES")
print("=" * 60)

zero_temp = df[df["temp"] == 0]

print("Zero-temperature records:", len(zero_temp))
print(zero_temp[
    ["date_time", "temp", "traffic_volume", "weather_main"]
].to_string(index=False))

print("\n" + "=" * 60)
print("RAINFALL ANOMALIES")
print("=" * 60)

high_rain = df[df["rain_1h"] > 100]

print("Records with rainfall > 100:", len(high_rain))
print(high_rain[
    ["date_time", "rain_1h", "temp",
     "traffic_volume", "weather_main", "weather_description"]
].to_string(index=False))

print("\nLargest rainfall values:")
print(df["rain_1h"].nlargest(10).to_string(index=False))

print("\nInspection complete. No data was modified.")
