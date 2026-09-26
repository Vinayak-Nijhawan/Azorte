"""
MOIL-GeoSync â€” Real Weather Data via Open-Meteo API
=====================================================
Pulls REAL historical weather data (rainfall, temperature) for 10 mine locations.

Source: Open-Meteo Historical Weather API (FREE, no API key needed!)
Data: Monthly aggregated rainfall and temperature for 2016-2025

Output: newdataset/weather_real.csv
"""

import requests
import pandas as pd
import numpy as np
import os
import time

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(OUTPUT_DIR, 'weather_real.csv')

# Real mine coordinates (approximate)
MINES = {
    # Maharashtra (Nagpur & Bhandara Districts)
    'Mine_A_Dongri_Buzurg': {'lat': 21.55, 'lon': 79.72, 'region': 'Maharashtra'},
    'Mine_B_Chikla':        {'lat': 21.52, 'lon': 79.75, 'region': 'Maharashtra'},
    'Mine_C_Munsar':        {'lat': 21.39, 'lon': 79.29, 'region': 'Maharashtra'},
    'Mine_E_Kandri':        {'lat': 21.40, 'lon': 79.27, 'region': 'Maharashtra'},
    'Mine_F_Gumgaon':       {'lat': 21.40, 'lon': 78.98, 'region': 'Maharashtra'},
    'Mine_G_Beldongri':     {'lat': 21.35, 'lon': 79.31, 'region': 'Maharashtra'},
    # Madhya Pradesh (Balaghat District)
    'Mine_D_Balaghat':      {'lat': 21.85, 'lon': 80.23, 'region': 'Madhya_Pradesh'},
    'Mine_H_Ukwa':          {'lat': 21.97, 'lon': 80.47, 'region': 'Madhya_Pradesh'},
    'Mine_I_Tirodi':        {'lat': 21.68, 'lon': 79.72, 'region': 'Madhya_Pradesh'},
    'Mine_J_Sitapatore':    {'lat': 21.72, 'lon': 79.80, 'region': 'Madhya_Pradesh'},
}

# Open-Meteo Historical Weather API (FREE, no key needed)
BASE_URL = "https://archive-api.open-meteo.com/v1/archive"


def fetch_weather_for_mine(mine_name, lat, lon, start_year=2016, end_year=2025):
    """Fetch daily weather data from Open-Meteo and aggregate to monthly."""
    all_monthly = []

    for year in range(start_year, end_year + 1):
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"

        params = {
            'latitude': lat,
            'longitude': lon,
            'start_date': start_date,
            'end_date': end_date,
            'daily': 'precipitation_sum,temperature_2m_max,temperature_2m_min,temperature_2m_mean',
            'timezone': 'Asia/Kolkata'
        }

        try:
            response = requests.get(BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if 'daily' not in data:
                print(f"[WARN]   {mine_name} {year}: No daily data")
                continue

            daily = data['daily']
            df_daily = pd.DataFrame({
                'date': pd.to_datetime(daily['time']),
                'rainfall_mm': daily['precipitation_sum'],
                'temp_max': daily['temperature_2m_max'],
                'temp_min': daily['temperature_2m_min'],
                'temp_mean': daily['temperature_2m_mean'],
            })

            # Aggregate to monthly
            df_daily['month'] = df_daily['date'].dt.month
            df_daily['year'] = df_daily['date'].dt.year

            monthly = df_daily.groupby(['year', 'month']).agg({
                'rainfall_mm': 'sum',
                'temp_max': 'max',
                'temp_min': 'min',
                'temp_mean': 'mean',
            }).reset_index()

            monthly['rainy_days'] = df_daily.groupby(['year', 'month']).apply(
                lambda x: (x['rainfall_mm'] > 2.5).sum()
            ).values

            all_monthly.append(monthly)

        except Exception as e:
            print(f"[WARN]   {mine_name} {year}: API error â€” {e}")

        time.sleep(0.5)  # Rate limit respect

    if not all_monthly:
        return pd.DataFrame()

    df = pd.concat(all_monthly, ignore_index=True)
    df['mine_id'] = mine_name
    df['latitude'] = lat
    df['longitude'] = lon

    return df


def main():
    print("=" * 70)
    print("MOIL-GeoSync â€” Real Historical Weather Data")
    print("Source: Open-Meteo API (FREE, no API key needed)")
    print("=" * 70)

    all_data = []

    for mine_name, info in MINES.items():
        lat, lon, region = info['lat'], info['lon'], info['region']
        print(f"\n[MINE] {mine_name} ({region})")
        print(f"[COORDS] {lat}ÂdegN, {lon}ÂdegE")

        df = fetch_weather_for_mine(mine_name, lat, lon)

        if df.empty:
            print(f"[WARN]   No data for {mine_name}")
            continue

        all_data.append(df)
        print(f"[INFO]   âœ… {len(df)} monthly records fetched")

    if not all_data:
        print("\n[ERROR] No weather data fetched!")
        return

    df_all = pd.concat(all_data, ignore_index=True)

    # Reorder columns
    cols = ['mine_id', 'latitude', 'longitude', 'year', 'month',
            'rainfall_mm', 'rainy_days', 'temp_max', 'temp_min', 'temp_mean']
    df_all = df_all[cols]

    # Save
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        f.write(f"# DATA SOURCE: REAL (Open-Meteo Historical Weather API)\n")
        f.write(f"# PERIOD: 2016-2025 (10 years, monthly aggregated)\n")
        f.write(f"# GENERATED: {pd.Timestamp.now().isoformat()}\n")
        f.write(f"# ALL values are REAL historical weather observations.\n")
        df_all.to_csv(f, index=False)

    print(f"\n{'=' * 70}")
    print(f"OUTPUT: {OUTPUT_PATH}")
    print(f"Total rows: {len(df_all)}")
    print(f"\nMine breakdown:")
    print(df_all['mine_id'].value_counts().to_string())
    print(f"\nRainfall stats (monthly mm):")
    print(df_all['rainfall_mm'].describe().round(2).to_string())
    print("\nâœ… DONE! Real weather data saved.")


if __name__ == '__main__':
    main()

