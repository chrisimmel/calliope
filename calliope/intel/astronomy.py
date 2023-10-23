import aiohttp
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from calliope.models import (
    Hemisphere,
    MAJOR_METEOR_SHOWERS,
    MeteorShowerModel,
    NightSkyObjectModel,
    SolarEclipseModel
)


def get_active_meteor_showers(
    hemisphere: Hemisphere,
    when: datetime,
) -> Tuple[List[MeteorShowerModel], List[MeteorShowerModel]]:
    active_meteor_showers = []
    peaking_meteor_showers = []

    for shower in MAJOR_METEOR_SHOWERS:
        start = date(when.year, shower.start_date.month, shower.start_date.day)
        end = date(when.year, shower.end_date.month, shower.end_date.day)
        if start <= when.date() <= end and hemisphere in shower.hemispheres:
            active_meteor_showers.append(shower)

            # Consider the shower to be peaking between 9am the morning before
            # the peak until 6am the morning of the peak. The actual peak is
            # always after midnight. This way we have a chance to talk about
            # the shower the eve of the peak, whether or not people are actually
            # awake to see the shower.
            peaking_midnight = datetime(
                shower.peak_morning.year,
                shower.peak_morning.month,
                shower.peak_morning.day,
                0, 0, 0, tzinfo=when.tzinfo
            )
            peaking_start = peaking_midnight - timedelta(hours=15)
            peaking_end = peaking_midnight + timedelta(hours=6)

            if peaking_start <= when <= peaking_end:
                peaking_meteor_showers.append((shower))

    return active_meteor_showers, peaking_meteor_showers


async def get_night_sky_objects(
    aiohttp_session: aiohttp.ClientSession,
    latitude: float,
    longitude: float
) -> List[NightSkyObjectModel]:
    """
    Gets information about what astronomical bodies are in the key at a given location
    and the present time.

    Args:
        aiohttp_session: the session to manage async IO requests.
        latitude: the latitude of the point of interest.
        longitude: the longitude of the point of interest.

    Returns:
        a NightSkyModel describing the objects currently in the night sky.
    """
    api_url = (
        f"https://api.visibleplanets.dev/v3/?latitude={latitude}&longitude={longitude}"
        # &time=2023-10-13T15:57:44Z
    )

    response = await aiohttp_session.get(api_url)
    json_response = await response.json()
    if not json_response:
        raise ValueError(f"No data returned from {api_url}.")

    data: List[Dict[str, Any]] = json_response.get("data", [])
    objects: List[NightSkyObjectModel] = [
        NightSkyObjectModel(
            name=object_data.get("name"),
            constellation=object_data.get("constellation"),
            above_horizon=object_data.get("aboveHorizon", False),
            magnitude=object_data.get("magnitude", 0.0),
            naked_eye_object=object_data.get("nakedEyeObject", False),
            phase=object_data.get("phase", None),
        )
        for object_data in data
    ]
    return objects


def _parse_eclipse_response(
    when: datetime,
    json_response: Dict[str, Any]
) -> Optional[SolarEclipseModel]:
    properties = json_response.get("properties")
    if properties:
        # Rarely, there will be an eclipse on this day.
        # Capture its description and start and end times.
        description = properties.get("description")
        local_data: List[Dict[str, Any]] = properties.get("local_data", [])
        if description:
            start_time = None
            end_time = None
            for entry in local_data:
                phenomenon = entry.get("phenomenon")
                time = entry.get("time")
                if phenomenon == "Eclipse Begins":
                    start_time = datetime.combine(
                        when.date(),
                        datetime.strptime(time, "%H:%M:%S.%f").time(),
                        when.tzinfo
                    )
                elif phenomenon == "Eclipse Ends":
                    end_time = datetime.combine(
                        when.date(),
                        datetime.strptime(time, "%H:%M:%S.%f").time(),
                        when.tzinfo
                    )
            if start_time and end_time:
                return SolarEclipseModel(
                    description=description,
                    start_time=start_time,
                    end_time=end_time,
                )
    return None


async def get_solar_eclipse_of_the_day(
    aiohttp_session: aiohttp.ClientSession,
    when: datetime,
    latitude: float,
    longitude: float,
    elevation: float,
) -> Optional[SolarEclipseModel]:
    """
    If there is a solar eclipse on the given day at the given location,
    describes the eclipse and gives its local start and end times.

    Args:
        aiohttp_session: the session to manage async IO requests.
        when: the datetime we're asking about.
        latitude: the latitude of the point of interest.
        longitude: the longitude of the point of interest.
        elevation: the elevation in meters of the point of interest.

    Returns:
        a SolarEclipseModel about the eclipse, if any, else None.
    """

    day = when.date().strftime("%Y-%m-%d")
    api_url = (
        "https://aa.usno.navy.mil/api/eclipses/solar/date"
        f"?date={day}&coords={latitude},{longitude}&height={int(elevation)}"
    )

    eclipse: Optional[SolarEclipseModel] = None

    try:
        response = await aiohttp_session.get(api_url)
        json_response = await response.json()
        if json_response:
            eclipse = _parse_eclipse_response(when, json_response)
    except Exception as e:
        print(f"Unable to get eclipse data: {e}")

    return eclipse
