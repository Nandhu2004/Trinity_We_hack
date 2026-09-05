import pandas as pd


DATA_FILE = "ml/data/carbon_history.csv"


def get_recent_carbon(zone, count=3):

    df = pd.read_csv(DATA_FILE)

    df["datetime"] = pd.to_datetime(
        df["datetime"],
        utc=True
    )

    zone_data = (
        df[df["zone"] == zone]
        .sort_values("datetime")
        .tail(count)
    )

    if len(zone_data) < count:
        raise ValueError(
            f"Not enough historical data for zone {zone}."
        )

    return zone_data["carbon_intensity"].tolist()