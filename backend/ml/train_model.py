import pandas as pd

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.preprocessing import LabelEncoder


INPUT_FILE = "ml/data/carbon_training.csv"
MODEL_FILE = "ml/carbon_model.pkl"


# Load training data
df = pd.read_csv(INPUT_FILE)

# Encode zone names into numbers
encoder = LabelEncoder()

df["zone_encoded"] = encoder.fit_transform(
    df["zone"]
)


# Features used by the model
features = [
    "zone_encoded",
    "hour",
    "day_of_week",
    "carbon_lag_1",
    "carbon_lag_2",
    "carbon_lag_3",
    "carbon_intensity"
]

target = "target_carbon"


X = df[features]
y = df[target]


# Time-based split
# First 80% = training
# Last 20% = testing
split_index = int(len(df) * 0.8)

X_train = X.iloc[:split_index]
X_test = X.iloc[split_index:]

y_train = y.iloc[:split_index]
y_test = y.iloc[split_index:]


# Create model
model = RandomForestRegressor(
    n_estimators=200,
    random_state=42,
    n_jobs=-1
)


# Train
print("Training model...")

model.fit(
    X_train,
    y_train
)


# Predict
predictions = model.predict(X_test)


# Evaluate
mae = mean_absolute_error(
    y_test,
    predictions
)

rmse = mean_squared_error(
    y_test,
    predictions
) ** 0.5


print("\nModel evaluation")
print("----------------")
print(f"Test samples: {len(X_test)}")
print(f"MAE: {mae:.2f} gCO2/kWh")
print(f"RMSE: {rmse:.2f} gCO2/kWh")


# Save model and encoder
import pickle

with open(MODEL_FILE, "wb") as file:
    pickle.dump(
        {
            "model": model,
            "encoder": encoder,
            "features": features
        },
        file
    )


print("\nModel saved.")
print(f"File: {MODEL_FILE}")