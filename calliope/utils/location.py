import aiohttp
from datetime import date, datetime
from ipaddress import ip_address
from typing import Any, Dict, Optional
import tzlocal
from zoneinfo import ZoneInfo

from calliope.models import (
    BasicLocationMetadataModel,
    CurrentWeatherModel,
    FullLocationMetadata,
    WMO_WEATHER_DESCRIPTIONS_BY_CODE,
)


def get_local_datetime(tz: str) -> datetime:
    """
    Gets the current local datetime in the given timezone.
    """
    if not tz:
        tz = tzlocal.get_localzone_name()
    return datetime.now(tz=ZoneInfo(tz))


def is_ip_private(ip: str) -> bool:
    """
    Determines whether the given IP address is private.
    """
    return ip_address(ip).is_private


async def get_public_ip_address(
        aiohttp_session: aiohttp.ClientSession
) -> Optional[str]:
    """
    Gets the public IP address of the current runtime environment.
    """
    api_url = "https://api.ipify.org?format=json"

    try:
        response = await aiohttp_session.get(api_url)
        json_response = await response.json()

        return json_response.get("ip") if json_response else None
    except Exception:
        return None


async def get_location_from_ip(
        aiohttp_session: aiohttp.ClientSession,
        ip: Optional[str]
) -> BasicLocationMetadataModel:
    """
    Gets the estimated location of a given IP address.
    """
    if not ip or is_ip_private(ip):
        ip = await get_public_ip_address(aiohttp_session)

    if not ip:
        return BasicLocationMetadataModel(ip_address=None)

    api_url = f"http://ip-api.com/json/{ip}"

    response = await aiohttp_session.get(api_url)
    json_response = await response.json()

    if json_response and json_response.get("status") == "success":
        return BasicLocationMetadataModel(
            country=json_response.get("country"),
            country_code=json_response.get("countryCode"),
            region_name=json_response.get("regionName"),
            city=json_response.get("city"),
            zip=json_response.get("zip"),
            lattitude=json_response.get("lat"),
            longitude=json_response.get("lon"),
            timezone=json_response.get("timezone"),
            isp=json_response.get("isp"),
            ip_address=ip,
        )
    else:
        # raise ValueError(f"Invalid location response: {json_response}")
        return BasicLocationMetadataModel(ip_address=None)


async def get_weather_at_location(
        aiohttp_session: aiohttp.ClientSession,
        lattitude: str,
        longitude: str
) -> CurrentWeatherModel:
    """
    Gets the weather at a given location.
    """
    api_url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={lattitude}&longitude={longitude}"
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
            weather_description=WMO_WEATHER_DESCRIPTIONS_BY_CODE.get(weather_code),
        )
    else:
        raise ValueError(f"Invalid weather result: {json_response}")


async def get_location_metadata_for_ip(
    aiohttp_session: aiohttp.ClientSession,
    ip: Optional[str]
) -> FullLocationMetadata:
    """
    Gets the full location metadata for a given IP address. This includes
    not only static information about the location (city, region, country name),
    but also transient things like weather, time of day, date, and season.
    """
    basic_metadata = await get_location_from_ip(aiohttp_session, ip)

    local_datetime = get_local_datetime(basic_metadata.timezone)

    if basic_metadata.lattitude and basic_metadata.longitude:
        weather_metadata = await get_weather_at_location(
            aiohttp_session,
            basic_metadata.lattitude,
            basic_metadata.longitude,
        )
    else:
        weather_metadata = None

    return FullLocationMetadata(
        location=basic_metadata,
        weather=weather_metadata,
        local_datetime=local_datetime,
    )


Y = 2000  # dummy leap year to allow input X-02-29 (leap day)


seasons = [
    ('winter', (date(Y, 1, 1), date(Y, 3, 20))),
    ('spring', (date(Y, 3, 21), date(Y, 6, 20))),
    ('summer', (date(Y, 6, 21), date(Y, 9, 22))),
    ('autumn', (date(Y, 9, 23), date(Y, 12, 20))),
    ('winter', (date(Y, 12, 21), date(Y, 12, 31)))
]


def get_season(now):
    if isinstance(now, datetime):
        now = now.date()
    now = now.replace(year=Y)
    return next(
        season for season, (start, end) in seasons
        if start <= now <= end
    )


def get_local_situation_text(
    image_analysis: Optional[Dict[str, Any]],
    location_metadata: FullLocationMetadata,
) -> str:
    """
    We want to give the LLM some situational context about what's happening
    where the client is running.

    What we want to hand the LLM is something like:

    Location:
    New York, New York, United States

    Scene:
    There is a tree with ripe oranges hanging from its branches. The tree is
    against a white wall, and there is a small fountain in front of it. The
    fountain has a small bowl on top of it, and there is a small green plant
    growing in the bowl. There is also a small bird perched on the edge of
    the fountain. A book rests on a table next to the fountain, with the
    words "The Lord of the Rings".

    Keywords:
    fruit, tree, branch, citrus, fruit tree, outdoor, calamondin
    orange, natural foods, leaf, oranges

    Text:
    "The Lord of the Rings", "Tolkien"

    Situation:
    The date is Wednesday, October 4th 2023.
    The time is 10:37 AM.
    The weather is: Clouds generally forming or developing during the past hour.
    The temperature is 12.2 degrees Celsius.
    The season is autumn.
    It is daytime.
    """
    situation_text = ""

    if location_metadata.location:
        situation_text += (
            "Location\n"
            f"{location_metadata.location.city}, "
            f" {location_metadata.location.region_name}, "
            f" {location_metadata.location.country}\n\n"
        )

    if image_analysis:
        situation_text += (
            "Scene:\n"
            f"{image_analysis.get('all_captions')}\n\n"
        )
        situation_text += f"Keywords:\n{image_analysis.get('all_tags_and_objects')}.\n\n"

        text = image_analysis.get("text")
        if text:
            situation_text += f"Text:\n{text}\n\n"

    situation_text += "Situation:\n"
    situation_text += (
        "\nThe date is "
        f"{location_metadata.local_datetime.strftime('%M %d, %Y')}.\n"
    )
    situation_text += (
        "The time is "
        f"{location_metadata.local_datetime.strftime('%H:%M')}.\n"
    )
    situation_text += (
        "It is currently "
        f"{'daytime' if location_metadata.weather.is_day else 'nighttime'}.\n"
    )
    situation_text += (
        "The season is "
        f"{get_season(location_metadata.local_datetime)}.\n"
    )

    if location_metadata.weather:
        # It would also be nice to know if there were big weather changes
        # expected in the next few hours, because that could be great to
        # introduce into a story. We'll start with just current weather,
        # though.
        situation_text += (
            "The weather is currently: "
            f"{location_metadata.weather.weather_description}.\n"
        )
        situation_text += (
            "The temperature is "
            f"{location_metadata.weather.temperature} degrees Celsius.\n"
        )

    return situation_text
