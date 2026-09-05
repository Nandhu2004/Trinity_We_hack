import pickle
import pandas as pd


MODEL_FILE = "ml/carbon_model.pkl"


# Load the trained model once
with open(MODEL_FILE, "rb") as file:
    saved = pickle.load(file)


model = saved["model"]
encoder = saved["encoder"]
features = saved["features"]


def predict_next_hour(
    zone,
    hour,
    day_of_week,
    carbon_lag_1,
    carbon_lag_2,
    carbon_lag_3,
    carbon_intensity
):
    """
    Predict the carbon intensity for the next hour.
    """

    # Check that the model knows this zone
    if zone not in encoder.classes_:
        raise ValueError(
            f"Zone '{zone}' was not seen during model training."
        )

    zone_encoded = encoder.transform([zone])[0]

    input_data = pd.DataFrame(
        [[
            zone_encoded,
            hour,
            day_of_week,
            carbon_lag_1,
            carbon_lag_2,
            carbon_lag_3,
            carbon_intensity
        ]],
        columns=features
    )

    prediction = model.predict(input_data)[0]

    return float(prediction)