import pandas as pd


INPUT_FILE = "ml/data/carbon_history.csv"
OUTPUT_FILE = "ml/data/carbon_training.csv"


# Load historical data
df = pd.read_csv(INPUT_FILE)

# Convert datetime to proper datetime format
df["datetime"] = pd.to_datetime(df["datetime"], utc=True)

# Sort each zone chronologically
df = df.sort_values(
    ["zone", "datetime"]
).reset_index(drop=True)


# Create time-based features
df["hour"] = df["datetime"].dt.hour
df["day_of_week"] = df["datetime"].dt.dayofweek


# Create historical lag features
df["carbon_lag_1"] = (
    df.groupby("zone")["carbon_intensity"]
    .shift(1)
)

df["carbon_lag_2"] = (
    df.groupby("zone")["carbon_intensity"]
    .shift(2)
)

df["carbon_lag_3"] = (
    df.groupby("zone")["carbon_intensity"]
    .shift(3)
)


# Target: carbon intensity one hour into the future
df["target_carbon"] = (
    df.groupby("zone")["carbon_intensity"]
    .shift(-1)
)


# Remove rows where lag/target values don't exist
df = df.dropna(
    subset=[
        "carbon_lag_1",
        "carbon_lag_2",
        "carbon_lag_3",
        "target_carbon"
    ]
)


# Select final training columns
training_df = df[
    [
        "datetime",
        "zone",
        "hour",
        "day_of_week",
        "carbon_lag_1",
        "carbon_lag_2",
        "carbon_lag_3",
        "carbon_intensity",
        "target_carbon"
    ]
]


# Save prepared dataset
training_df.to_csv(
    OUTPUT_FILE,
    index=False
)


print("Training dataset created.")
print(f"Rows: {len(training_df)}")
print(f"Zones: {training_df['zone'].nunique()}")
print(f"File: {OUTPUT_FILE}")
print("\nRows per zone:")
print(training_df["zone"].value_counts())