import asyncio

from services.electricity_maps import get_latest_carbon


ZONES = [
    "DE",
    "FR",
    "BE",
    "NL",
    "DK",
]


async def main():

    print("\nTesting Electricity Maps zones...\n")

    for zone in ZONES:

        try:

            data = await get_latest_carbon(zone)

            print(
                f"{zone}: "
                f"{data.get('carbonIntensity')} gCO2e/kWh"
            )

        except Exception as e:

            print(
                f"{zone}: ERROR - {e}"
            )


asyncio.run(main())