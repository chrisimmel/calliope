import aiohttp
from ipaddress import ip_address
from typing import Any, Dict, Optional

from calliope.intel.time import get_local_datetime, get_season
from calliope.intel.astronomy import (
    get_active_meteor_showers, get_night_sky_objects, get_solar_eclipse_of_the_day
)
from calliope.intel.weather import get_weather_at_location
from calliope.models import (
    BasicLocationMetadataModel,
    FullLocationMetadata,
    Hemisphere
)
from calliope.utils.text import format_sequence


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


def hemisphere_at_latitude(latitude: float) -> Hemisphere:
    return Hemisphere.SOUTHERN if latitude < 0 else Hemisphere.NORTHERN


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
        latitude = json_response.get("lat")
        longitude = json_response.get("lon")

        return BasicLocationMetadataModel(
            country=json_response.get("country"),
            country_code=json_response.get("countryCode"),
            region_name=json_response.get("regionName"),
            city=json_response.get("city"),
            zip=json_response.get("zip"),
            latitude=latitude,
            longitude=longitude,
            hemisphere=hemisphere_at_latitude(latitude),
            timezone=json_response.get("timezone"),
            isp=json_response.get("isp"),
            ip_address=ip,
        )
    else:
        # raise ValueError(f"Invalid location response: {json_response}")
        return BasicLocationMetadataModel(ip_address=None)


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

    local_datetime = (
        get_local_datetime(basic_metadata.timezone) if basic_metadata.timezone else None
    )

    if basic_metadata.latitude and basic_metadata.longitude:
        weather_metadata = await get_weather_at_location(
            aiohttp_session,
            basic_metadata.latitude,
            basic_metadata.longitude,
        )
        night_sky_objects = await get_night_sky_objects(
            aiohttp_session,
            basic_metadata.latitude,
            basic_metadata.longitude,
        ) if weather_metadata and not weather_metadata.is_day else []

        active_meteor_showers, peaking_meteor_showers = get_active_meteor_showers(
            basic_metadata.hemisphere, local_datetime
        )
        solar_eclipse = await get_solar_eclipse_of_the_day(
            aiohttp_session,
            local_datetime,
            basic_metadata.latitude,
            basic_metadata.longitude,
            weather_metadata.elevation if weather_metadata else 0,
        )
    else:
        weather_metadata = None
        night_sky_objects = []
        active_meteor_showers = []
        peaking_meteor_showers = []
        solar_eclipse = None

    print(f"{basic_metadata=}, {solar_eclipse=}, {weather_metadata=}")

    return FullLocationMetadata(
        location=basic_metadata,
        weather=weather_metadata,
        local_datetime=local_datetime,
        night_sky_objects=night_sky_objects,
        active_meteor_showers=active_meteor_showers,
        peaking_meteor_showers=peaking_meteor_showers,
        solar_eclipse=solar_eclipse,
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
    if location_metadata.local_datetime:
        situation_text += (
            "\nThe date is "
            f"{location_metadata.local_datetime.strftime('%A, %B %d, %Y')}.\n"
        )
        situation_text += (
            "The time is "
            f"{location_metadata.local_datetime.strftime('%H:%M')}.\n"
        )
    if location_metadata.weather:
        is_day = location_metadata.weather.is_day
        situation_text += (
            f"It is currently {'daytime' if is_day else 'nighttime'}.\n"
        )
    if location_metadata.local_datetime:
        situation_text += (
            "The season is "
            f"{get_season(location_metadata.local_datetime)}.\n"
        )

    if location_metadata.solar_eclipse:
        situation_text += (
            "Step outside today to see a solar eclipse!\n"
            f"{location_metadata.solar_eclipse.description} "
            f"Starting {location_metadata.solar_eclipse.start_time.strftime('%H:%M')}, "
            f"Ending {location_metadata.solar_eclipse.end_time.strftime('%H:%M')}, "
            "\n"
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

    if len(location_metadata.peaking_meteor_showers):
        for shower in location_metadata.peaking_meteor_showers:
            situation_text += (
                f"The {shower.name} meteor shower will peak tonight!\n"
            )
    elif (
        len(location_metadata.active_meteor_showers)
        and not location_metadata.weather.is_day
    ):
        for shower in location_metadata.active_meteor_showers:
            situation_text += (
                f"The {shower.name} meteor shower is active tonight.\n"
            )

    if len(location_metadata.night_sky_objects):
        object_names = []
        full_moon = False

        for sky_object in location_metadata.night_sky_objects:
            if sky_object.name == "The Moon":
                if sky_object.phase > 99 or sky_object.phase < 1:
                    full_moon = True

            if sky_object.naked_eye_object:
                object_names.append(sky_object.name)

        if len(object_names) > 1:
            situation_text += (
                f"{format_sequence(object_names)} are in the sky tonight.\n"
            )
        elif len(object_names) == 1:
            situation_text += f"{object_names[0]} is in the sky tonight.\n"

        if full_moon:
            situation_text += "The moon is full.\n"

    return situation_text
