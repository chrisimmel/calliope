import aiohttp

from calliope.models import CurrentWeatherModel, WMO_WEATHER_DESCRIPTIONS_BY_CODE


async def get_weather_at_location(
    aiohttp_session: aiohttp.ClientSession,
    latitude: float,
    longitude: float
) -> CurrentWeatherModel:
    """
    Gets the weather at a given location.
    """
    api_url = (
        "https://api.open-meteo.com/v1/forecast?"
        f"latitude={latitude}&longitude={longitude}"
        "&current_weather=true&"
        # "hourly=temperature_2m,relativehumidity_2m,windspeed_10m"
    )

    response = await aiohttp_session.get(api_url)
    json_response = await response.json()
    if json_response and not json_response.get("error", False):
        current_weather = json_response.get("current_weather")
        weather_code = current_weather.get("weathercode", 0)
        return CurrentWeatherModel(
            time=current_weather.get("time"),
            temperature=current_weather.get("temperature"),
            elevation=json_response.get("elevation"),
            wind_speed=current_weather.get("windspeed"),
            wind_direction=current_weather.get("winddirection"),
            is_day=current_weather.get("is_day"),
            weather_code=weather_code,
            weather_description=(
                WMO_WEATHER_DESCRIPTIONS_BY_CODE.get(weather_code) or "(unknown)"
            ),
        )
    else:
        raise ValueError(f"Invalid weather result: {json_response}")
