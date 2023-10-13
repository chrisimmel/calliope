from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class BasicLocationMetadataModel(BaseModel):
    country: Optional[str] = None
    country_code: Optional[str] = None
    region_name: Optional[str] = None
    city: Optional[str] = None
    zip: Optional[str] = None
    lattitude: Optional[float] = None
    longitude: Optional[float] = None
    timezone: Optional[str] = None
    isp: Optional[str] = None
    ip_address: Optional[str] = None


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
    4: "Haze or smoke, or dust in suspension in the air, visibility equal to, or greater than, 1 km",
    5: "Haze or smoke, or dust in suspension in the air, visibility less than 1 km",
    10: "Mist",
    11: "Diamond dust",
    12: "Distant lightning",
    18: "Squalls",

    # Code figures 20-26 are used to report precipitation, fog (or ice fog) or
    # thunderstorm at the station  during the preceding hour but not at the time
    # of observation.

    20: "Fog",
    21: "PRECIPITATION",
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
    40: "PRECIPITATION",
    41: "Precipitation, slight or moderate",
    42: "Precipitation, heavy",
    43: "Liquid precipitation, slight or moderate",
    44: "Liquid precipitation, heavy",
    45: "Solid precipitation, slight or moderate",
    46: "Solid precipitation, heavy",
    47: "Freezing precipitation, slight or moderate",
    48: "Freezing precipitation, heavy",
    50: "DRIZZLE",
    51: "Drizzle, not freezing, slight",
    52: "Drizzle, not freezing, moderate",
    53: "Drizzle, not freezing, heavy",
    54: "Drizzle, freezing, slight",
    55: "Drizzle, freezing, moderate",
    56: "Drizzle, freezing, heavy",
    57: "Drizzle and rain, slight",
    58: "Drizzle and rain, moderate or heavy",
    60: "RAIN",
    61: "Rain, not freezing, slight",
    62: "Rain, not freezing, moderate",
    63: "Rain, not freezing, heavy",
    64: "Rain, freezing, slight",
    65: "Rain, freezing, moderate",
    66: "Rain, freezing, heavy",
    67: "Rain (or drizzle) and snow, slight",
    68: "Rain (or drizzle) and snow, moderate or heavy",
    70: "SNOW",
    71: "Snow, slight",
    72: "Snow, moderate",
    73: "Snow, heavy",
    74: "Ice pellets, slight",
    75: "Ice pellets, moderate",
    76: "Ice pellets, heavy",
    77: "Snow grains",
    78: "Ice crystals",
    80: "SHOWER(S) or INTERMITTENT PRECIPITATION",
    81: "Rain shower(s) or intermittent rain, slight",
    82: "Rain shower(s) or intermittent rain, moderate",
    83: "Rain shower(s) or intermittent rain, heavy",
    84: "Rain shower(s) or intermittent rain, violent",
    85: "Snow shower(s) or intermittent snow, slight",
    86: "Snow shower(s) or intermittent snow, moderate",
    87: "Snow shower(s) or intermittent snow, heavy",
    89: "Hail",
    90: "THUNDERSTORM",
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
    # THe Sun:  −26.7
    # The full Moon: −11
    # Sirius: −1.5
    #
    # Britannica: https://www.britannica.com/science/magnitude-astronomy
    magnitude: float

    # Whether we can expect to see this with the naked eye. 
    naked_eye_object: bool

    # Phase is full at 100, then immediately drops to zero
    # and climbs back to a hundred. So it is waning from 0
    # to 50, then is waxing from 50 up to 100.
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


class NightSkyModel(BaseModel):
    time: str
    objects: List[NightSkyObjectModel]


class FullLocationMetadata(BaseModel):
    location: BasicLocationMetadataModel
    weather: Optional[CurrentWeatherModel] = None
    local_datetime: Optional[datetime] = None
    night_sky_data: Optional[NightSkyModel] = None
