import pickle
import pandas as pd


MODEL_FILE = "ml/carbon_model.pkl"
DATA_FILE = "ml/data/carbon_training.csv"


# Load trained model
with open(MODEL_FILE, "rb") as file:
    saved = pickle.load(file)

model = saved["model"]
encoder = saved["encoder"]
features = saved["features"]


# Load prepared data
df = pd.read_csv(DATA_FILE)

# Pick the latest record from each zone
latest = (
    df.sort_values("datetime")
    .groupby("zone")
    .tail(1)
    .copy()
)


# Encode zones
latest["zone_encoded"] = encoder.transform(
    latest["zone"]
)


# Prepare model input
X = latest[features]


# Predict next-hour carbon intensity
latest["predicted_next_hour"] = model.predict(X)


print("\nNext-hour carbon predictions")
print("----------------------------")

for _, row in latest.iterrows():

    print(
        f"{row['zone']:12} → "
        f"{row['predicted_next_hour']:.2f} gCO2/kWh"
    )