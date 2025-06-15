from datetime import date, datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


class Hemisphere(Enum):
    NORTHERN = "northern"
    SOUTHERN = "southern"


class BasicLocationMetadataModel(BaseModel):
    country: Optional[str] = None
    country_code: Optional[str] = None
    region_name: Optional[str] = None
    city: Optional[str] = None
    zip: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timezone: Optional[str] = None
    isp: Optional[str] = None
    ip_address: Optional[str] = None
    hemisphere: Optional[Hemisphere] = None


class CurrentWeatherModel(BaseModel):
    time: str
    temperature: float
    elevation: float
    wind_speed: float
    wind_direction: float
    is_day: bool
    weather_code: int
    weather_description: str


# A table of weather descriptions by WMO code, taken from
# https://artefacts.ceda.ac.uk/badc_datadocs/surface/code.html.
WMO_WEATHER_DESCRIPTIONS_BY_CODE = {
    0: "No significant weather observed",
    1: "Clouds generally dissolving or becoming less developed during the past hour",
    2: "State of sky on the whole unchanged during the past hour",
    3: "Clouds generally forming or developing during the past hour",
    4: (
        "Haze or smoke, or dust in suspension in the air, visibility equal to, or "
        "greater than, 1 km"
    ),
    5: "Haze or smoke, or dust in suspension in the air, visibility less than 1 km",
    10: "Mist",
    11: "Diamond dust",
    12: "Distant lightning",
    18: "Squalls",

    # Code figures 20-26 are used to report precipitation, fog (or ice fog) or
    # thunderstorm at the station  during the preceding hour but not at the time
    # of observation.

    20: "Fog",
    21: "Precipitation",
    22: "Drizzle (not freezing) or snow grains",
    23: "Rain (not freezing)",
    24: "Snow",
    25: "Freezing drizzle or freezing rain",
    26: "Thunderstorm (with or without precipitation)",
    27: "BLOWING OR DRIFTING SNOW OR SAND",
    28: "Blowing or drifting snow or sand, visibility equal to, or greater than, 1 km",
    29: "Blowing or drifting snow or sand, visibility less than 1 km",
    30: "FOG",
    31: "Fog or ice fog in patches",
    32: "Fog or ice fog, has become thinner during the past hour",
    33: "Fog or ice fog, no appreciable change during the past hour",
    34: "Fog or ice fog, has begun or become thicker during the past hour",
    35: "Fog, depositing rime",
    40: "Precipitation",
    41: "Precipitation, slight or moderate",
    42: "Precipitation, heavy",
    43: "Liquid precipitation, slight or moderate",
    44: "Liquid precipitation, heavy",
    45: "Solid precipitation, slight or moderate",
    46: "Solid precipitation, heavy",
    47: "Freezing precipitation, slight or moderate",
    48: "Freezing precipitation, heavy",
    50: "Drizzle",
    51: "Drizzle, not freezing, slight",
    52: "Drizzle, not freezing, moderate",
    53: "Drizzle, not freezing, heavy",
    54: "Drizzle, freezing, slight",
    55: "Drizzle, freezing, moderate",
    56: "Drizzle, freezing, heavy",
    57: "Drizzle and rain, slight",
    58: "Drizzle and rain, moderate or heavy",
    60: "Rain",
    61: "Rain, not freezing, slight",
    62: "Rain, not freezing, moderate",
    63: "Rain, not freezing, heavy",
    64: "Rain, freezing, slight",
    65: "Rain, freezing, moderate",
    66: "Rain, freezing, heavy",
    67: "Rain (or drizzle) and snow, slight",
    68: "Rain (or drizzle) and snow, moderate or heavy",
    70: "Snow",
    71: "Snow, slight",
    72: "Snow, moderate",
    73: "Snow, heavy",
    74: "Ice pellets, slight",
    75: "Ice pellets, moderate",
    76: "Ice pellets, heavy",
    77: "Snow grains",
    78: "Ice crystals",
    80: "Showers or intermittent precipitation",
    81: "Rain shower(s) or intermittent rain, slight",
    82: "Rain shower(s) or intermittent rain, moderate",
    83: "Rain shower(s) or intermittent rain, heavy",
    84: "Rain shower(s) or intermittent rain, violent",
    85: "Snow shower(s) or intermittent snow, slight",
    86: "Snow shower(s) or intermittent snow, moderate",
    87: "Snow shower(s) or intermittent snow, heavy",
    89: "Hail",
    90: "Thunderstorm",
    91: "Thunderstorm, slight or moderate, with no precipitation",
    92: "Thunderstorm, slight or moderate, with rain showers and/or snow showers",
    93: "Thunderstorm, slight or moderate, with hail",
    94: "Thunderstorm, heavy, with no precipitation",
    95: "Thunderstorm, heavy, with rain showers and/or snow showers",
    96: "Thunderstorm, heavy, with hail",
    99: "Tornado",
}


class NightSkyObjectModel(BaseModel):
    # The object's name (Sun, Moon, Venus, etc.)
    name: str

    # In what constellation the object currently appears.
    constellation: str

    # Whether the object is presently above the horizon.
    above_horizon: bool

    # The brightness of an object as it appears to an observer
    # at the given location. Smaller is brighter.
    # For reference:
    # The Sun:  −26.7
    # The full Moon: −11
    # Sirius: −1.5
    #
    # Britannica: https://www.britannica.com/science/magnitude-astronomy
    magnitude: float

    # Whether we can expect to see this with the naked eye.
    naked_eye_object: bool

    # Phase is new at 0, full at 50, and continues to climb to 100.
    # So it is waxing from 0 to 50, then waning from 50 up to 100.
    # Only present in the case of the moon.
    phase: Optional[float] = None

    """
    Unused:
    rightAscension: {
        "negative": false,
        "hours": 13,
        "minutes": 17,
        "seconds": 19.3,
        "raw": 13.288689508824122
    },
    "declination": {
        "negative": true,
        "degrees": 8,
        "arcminutes": 9,
        "arcseconds": 21,
        "raw": -8.155822096208393
    },
    "altitude": 17.71533237752294,
    "azimuth": 110.12246355292802,
    """


class SolarEclipseModel(BaseModel):
    description: str
    start_time: datetime
    end_time: datetime


class MeteorShowerModel(BaseModel):
    # The name of the shower.
    name: str

    # The hemispheres in which the shower is normally visible.
    hemispheres: List[Hemisphere]

    # The expected peak zenith hourly rate.
    zenith_hourly_rate: int

    # The start date (ignore the year).
    start_date: date

    # The date of the peak (ignore the year).
    peak_morning: date

    # The end date (ignore the year).
    end_date: date

    # Whether to look before midnight.
    before_midnight: bool = False


"""
From: https://www.amsmeteors.org/meteor-showers/2020-meteor-shower-list/

Quadrantids (QUA)	Dec 26-Jan 16	Jan 04	283.3°	15:20	+49.7°	40.2	2.1	120	0500	13
Lyrids (LYR)	Apr 15-Apr 29	Apr 23	032.4°	18:10	+33.3°	46.8	2.1	18	0400	02
eta Aquarids (ETA)	Apr 15-May 27	May 06	046.2°	22:30	-01.1°	65.5	2.4	60	0400	15
Perseids (PER)	Jul 14-Sep 01	Aug 13	140.0°	03:13	+58.0°	58.8	2.6	100	0400	27
Orionids (ORI)	Sep 26-Nov 22	Oct 22	207.5°	06:21	+15.6°	66.1	2.5	23	0500	07
Leonids (LEO)	Nov 03-Dec 02	Nov 18	236.0°	10:17	+21.6°	70.0	2.5	15	0500	05
Geminids (GEM)	Nov 19-Dec 24	Dec 14	262°0	07:34	+32.3°	33.8	2.6	120	0100	02
Ursids (URS)	Dec 13-Dec 24	Dec 22	270°5	14:36	+75.3°	33.0	3.0	10	0500	10
"""

MAJOR_METEOR_SHOWERS = [
    MeteorShowerModel(
        name="Quadrantids",
        hemispheres=[Hemisphere.NORTHERN],
        zenith_hourly_rate=120,
        start_date=date(2000, 12, 26),
        peak_morning=date(2000, 1, 4),
        end_date=date(2000, 1, 16),
    ),
    MeteorShowerModel(
        name="Lyrids",
        hemispheres=[Hemisphere.NORTHERN],
        zenith_hourly_rate=18,
        start_date=date(2000, 4, 15),
        peak_morning=date(2000, 4, 23),
        end_date=date(2000, 4, 29),
    ),
    MeteorShowerModel(
        name="eta Aquarids",
        hemispheres=[Hemisphere.NORTHERN],
        zenith_hourly_rate=60,
        start_date=date(2000, 4, 15),
        peak_morning=date(2000, 5, 6),
        end_date=date(2000, 5, 26),
    ),
    # Omitting the Southern delta Aquarids because they overlap
    # with the Perseids and are less intense and lesser known.
    MeteorShowerModel(
        name="Perseids",
        hemispheres=[Hemisphere.NORTHERN],
        zenith_hourly_rate=100,
        start_date=date(2000, 7, 14),
        peak_morning=date(2000, 8, 13),
        end_date=date(2000, 9, 1),
    ),
    MeteorShowerModel(
        name="Orionids",
        hemispheres=[Hemisphere.NORTHERN],
        zenith_hourly_rate=23,
        start_date=date(2000, 9, 26),
        peak_morning=date(2000, 10, 22),
        end_date=date(2000, 11, 22),
    ),
    MeteorShowerModel(
        name="Leonids",
        hemispheres=[Hemisphere.NORTHERN],
        zenith_hourly_rate=15,
        start_date=date(2000, 11, 3),
        peak_morning=date(2000, 11, 18),
        end_date=date(2000, 12, 2),
    ),
    MeteorShowerModel(
        name="Geminids",
        hemispheres=[Hemisphere.NORTHERN, Hemisphere.SOUTHERN],
        zenith_hourly_rate=120,
        start_date=date(2000, 11, 19),
        peak_morning=date(2000, 12, 14),
        end_date=date(2000, 12, 24),
        before_midnight=True,
    ),
    # Omitting the Ursids because of low zhr.
]


class FullLocationMetadata(BaseModel):
    location: BasicLocationMetadataModel
    weather: Optional[CurrentWeatherModel] = None
    local_datetime: Optional[datetime] = None
    night_sky_objects: List[NightSkyObjectModel] = []
    active_meteor_showers: List[MeteorShowerModel] = []
    peaking_meteor_showers: List[MeteorShowerModel] = []
    solar_eclipse: Optional[SolarEclipseModel] = None
