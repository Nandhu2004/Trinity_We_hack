import asyncio
import csv
import os
from datetime import datetime, timedelta, timezone

import httpx
from dotenv import load_dotenv


# Load API key from backend/.env
BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(ENV_PATH)

API_KEY = os.getenv("ELECTRICITY_MAPS_API_KEY")

BASE_URL = "https://api.electricitymaps.com/v4"


async def get_zones(client):

    url = f"{BASE_URL}/zones"

    response = await client.get(
        url,
        headers={"auth-token": API_KEY}
    )

    response.raise_for_status()

    zones = response.json()

    usable_zones = [
        zone
        for zone, info in zones.items()
        if "carbon-intensity/past-range"
        in info.get("access", [])
    ]

    return usable_zones


async def get_historical_carbon(
    client,
    zone,
    start_datetime,
    end_datetime
):

    url = f"{BASE_URL}/carbon-intensity/past-range"

    params = {
        "zone": zone,
        "start": start_datetime,
        "end": end_datetime,
        "temporalGranularity": "hourly"
    }

    response = await client.get(
        url,
        headers={"auth-token": API_KEY},
        params=params
    )

    response.raise_for_status()

    return response.json()


async def collect_zone(

    client,
    zone,
    start_time,
    end_time
):

    all_records = []

    current_start = start_time

    while current_start < end_time:

        current_end = min(
            current_start + timedelta(days=9),
            end_time
        )

        try:

            data = await get_historical_carbon(
                client,
                zone,
                current_start.isoformat(),
                current_end.isoformat()
            )

            records = data.get("data", [])

            # Keep only actual historical measurements
            # and remove estimated values.
            for record in records:

                if record.get("isEstimated", False):
                    continue

                all_records.append([
                    record["datetime"],
                    record["zone"],
                    record["carbonIntensity"]
                ])

        except Exception as e:

            print(
                f"{zone} → FAILED for "
                f"{current_start} to {current_end}: {e}"
            )

        current_start = current_end

    print(
        f"{zone} → {len(all_records)} records"
    )

    return all_records


async def main():

    # Collect the last 30 days
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=30)

    async with httpx.AsyncClient(
        timeout=30.0
    ) as client:

        print("Discovering available zones...")

        usable_zones = await get_zones(client)

        print(
            f"Usable zones found: {len(usable_zones)}"
        )

        # Automatically select 20 zones
        selected_zones = ["DE", "FR", "GB"]

        print(
            f"Collecting data from "
            f"{len(selected_zones)} zones..."
        )

        tasks = [
            collect_zone(
                client,
                zone,
                start_time,
                end_time
            )
            for zone in selected_zones
        ]

        results = await asyncio.gather(*tasks)

    # Combine all zone results
    all_records = []

    for result in results:
        all_records.extend(result)

    # Save dataset
    output_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "data",
        "carbon_history.csv"
    )

    # Make sure data folder exists
    os.makedirs(
        os.path.dirname(output_file),
        exist_ok=True
    )

    with open(
        output_file,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.writer(file)

        writer.writerow([
            "datetime",
            "zone",
            "carbon_intensity"
        ])

        writer.writerows(all_records)

    print("\nDataset collection complete.")

    print(
        f"Total records saved: "
        f"{len(all_records)}"
    )

    print(
        f"File: {output_file}"
    )


if __name__ == "__main__":
    asyncio.run(main())