"""Execute the preprocessing pipeline on collected CCTV data."""
import os
import pandas as pd
import numpy as np
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
raw_meta_path = DATA_DIR / "raw_cctv_metadata.csv"
cam_path = DATA_DIR / "cameras.csv"

if not raw_meta_path.exists():
    print(f"Error: {raw_meta_path} does not exist.")
    exit(1)

df_raw = pd.read_csv(raw_meta_path)
df_cams = pd.read_csv(cam_path) if cam_path.exists() else pd.DataFrame()

print(f"=== CCTV SEMARANG: PREPROCESSING PIPELINE ===")
print(f"Total raw observations: {len(df_raw)}")

# 1. Parsing timestamp
df_clean = df_raw.copy()
df_clean['capture_timestamp'] = pd.to_datetime(df_clean['capture_timestamp'], errors='coerce')

# 2. Filter stream errors & log downtime
total_attempts = len(df_clean)
offline_count = (df_clean['capture_status'] != 'captured').sum()
print(f"Total capture attempts : {total_attempts}")
print(f"Stream error / offline : {offline_count} ({offline_count / total_attempts * 100:.1f}%)")
print(f"Captured successfully  : {total_attempts - offline_count}")

df_valid = df_clean[df_clean['capture_status'] == 'captured'].copy()

# 3. Numeric conversion
for col in ['resolution_w', 'resolution_h', 'mean_luminance', 'laplacian_variance']:
    df_valid[col] = pd.to_numeric(df_valid[col], errors='coerce')

# 4. Stream freeze / duplicate check
dup_count = df_valid['is_duplicate_of_previous'].astype(str).str.lower().isin(['true', '1']).sum()
print(f"Stream freeze / duplicates detected: {dup_count}")

# 5. Descriptive statistics (Mean, Var, Std)
print("\n--- Descriptive Statistics per Camera ---")
stat_table = df_valid.groupby(['camera_id', 'camera_name']).agg({
    'mean_luminance': ['count', 'mean', 'var', 'std'],
    'laplacian_variance': ['mean', 'var', 'std']
})
stat_table.columns = ['Count', 'Lum_Mean', 'Lum_Var', 'Lum_Std', 'Sharp_Mean', 'Sharp_Var', 'Sharp_Std']
print(stat_table.round(2).to_string())

# 6. IQR Outlier Detection
def detect_iqr_outliers(series):
    Q1 = series.quantile(0.25)
    Q3 = series.quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    return (series < lower_bound) | (series > upper_bound)

df_valid['is_luminance_outlier'] = detect_iqr_outliers(df_valid['mean_luminance'])
df_valid['is_sharpness_outlier'] = detect_iqr_outliers(df_valid['laplacian_variance'])
print(f"\nLuminance outliers (IQR): {df_valid['is_luminance_outlier'].sum()}")
print(f"Sharpness outliers (IQR): {df_valid['is_sharpness_outlier'].sum()}")

# 7. Merge Geospatial & Temporal Features
if not df_cams.empty:
    df_enriched = df_valid.merge(df_cams[['camera_id', 'zone', 'latitude', 'longitude']], on='camera_id', how='left')
else:
    df_enriched = df_valid

df_enriched['hour'] = df_enriched['capture_timestamp'].dt.hour
df_enriched['minute'] = df_enriched['capture_timestamp'].dt.minute
df_enriched['is_rush_hour'] = df_enriched['capture_timestamp'].apply(
    lambda ts: 1 if (ts.hour == 6 and ts.minute >= 30) or (ts.hour == 7) or (ts.hour == 8 and ts.minute <= 30) else 0
)

# 8. Normalization (MinMaxScaler)
lum_min, lum_max = df_enriched['mean_luminance'].min(), df_enriched['mean_luminance'].max()
df_enriched['mean_luminance_scaled'] = (df_enriched['mean_luminance'] - lum_min) / (lum_max - lum_min + 1e-6)

sharp_min, sharp_max = df_enriched['laplacian_variance'].min(), df_enriched['laplacian_variance'].max()
df_enriched['laplacian_variance_scaled'] = (df_enriched['laplacian_variance'] - sharp_min) / (sharp_max - sharp_min + 1e-6)

# 9. Save clean dataset
clean_path = DATA_DIR / "clean_cctv_metadata.csv"
df_enriched.to_csv(clean_path, index=False)
print(f"\n[SUCCESS] Clean dataset exported to: {clean_path}")
print(f"Dimensions: {df_enriched.shape[0]} rows x {df_enriched.shape[1]} columns")
