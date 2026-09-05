import asyncio
import httpx

from services.electricity_maps import API_KEY, BASE_URL


async def main():

    url = f"{BASE_URL}/zones"

    headers = {
        "auth-token": API_KEY
    }

    async with httpx.AsyncClient(timeout=30.0) as client:

        response = await client.get(
            url,
            headers=headers
        )

        response.raise_for_status()

        zones = response.json()

    countries = set()

    for zone_info in zones.values():

        country = zone_info.get("countryCode")

        if country:
            countries.add(country)

    print(f"Total zones: {len(zones)}")
    print(f"Unique country codes: {len(countries)}")

    print("\nFirst 50 country codes:")

    for country in sorted(countries)[:50]:
        print(country)


if __name__ == "__main__":
    asyncio.run(main())