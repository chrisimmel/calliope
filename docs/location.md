# Location Module

The `calliope.location` module provides functionality for adding contextual environmental awareness to Calliope's storytelling capabilities. It collects and integrates information about the client's physical location, local time, weather conditions, astronomical events, and other environmental factors that can enhance immersion and relevance in generated stories.

## Overview

This module enables Calliope to be aware of:

- **Geolocation**: Country, city, region, timezone based on IP address
- **Time Context**: Local time, date, and season
- **Weather Conditions**: Current temperature, conditions, and day/night status
- **Astronomical Events**: 
  - Visible planets and objects in the night sky
  - Moon phase information
  - Active or peaking meteor showers
  - Solar eclipses

These contextual elements allow Calliope to craft stories that are responsive to and incorporate the user's real-world environment, enhancing the personalized experience for users.

## Module Structure

The location module is organized into several sub-modules:

- **location.py**: Core functions for getting physical location from IP address and combining all location-based metadata
- **time.py**: Time-related utilities for determining local time and seasons
- **weather.py**: Functions to retrieve current weather conditions
- **astronomy.py**: Functions for identifying visible celestial objects and astronomical events

## Key Classes and Models

The module uses several Pydantic models (defined in `calliope.models.location_metadata`) to represent location data:

- `BasicLocationMetadataModel`: Basic geolocation information
- `CurrentWeatherModel`: Current weather conditions
- `NightSkyObjectModel`: Information about celestial objects in the night sky
- `MeteorShowerModel`: Information about active meteor showers
- `SolarEclipseModel`: Information about solar eclipses
- `FullLocationMetadata`: Comprehensive container for all location-related data

## Usage

The primary entry point to the location module is the `get_location_metadata_for_ip` function. This function orchestrates the collection of all location-related data and returns a comprehensive `FullLocationMetadata` object that can be used by storytelling strategies.

### Example Usage

```python
import httpx
from calliope.location.location import get_location_metadata_for_ip

async def get_story_context(client_ip: str):
    async with httpx.AsyncClient() as client:
        # Get full location metadata for the client's IP address
        location_metadata = await get_location_metadata_for_ip(client, client_ip)
        
        # Access location information
        if location_metadata.location.city:
            print(f"Client is located in {location_metadata.location.city}, {location_metadata.location.country}")
        
        # Access weather information
        if location_metadata.weather:
            print(f"Current weather: {location_metadata.weather.weather_description}")
            print(f"Temperature: {location_metadata.weather.temperature}°C")
        
        # Access astronomical information
        if location_metadata.night_sky_objects and not location_metadata.weather.is_day:
            print("Visible in tonight's sky:")
            for obj in location_metadata.night_sky_objects:
                if obj.naked_eye_object and obj.above_horizon:
                    print(f"- {obj.name} in {obj.constellation}")
                    
        # Check for special astronomical events
        if location_metadata.peaking_meteor_showers:
            for shower in location_metadata.peaking_meteor_showers:
                print(f"The {shower.name} meteor shower is peaking tonight!")
        
        if location_metadata.solar_eclipse:
            print(f"Solar eclipse today: {location_metadata.solar_eclipse.description}")
            print(f"  Starts: {location_metadata.solar_eclipse.start_time.strftime('%H:%M')}")
            print(f"  Ends: {location_metadata.solar_eclipse.end_time.strftime('%H:%M')}")
```

### Generating Context for LLMs

The module provides a utility function `get_local_situation_text()` that formats all the location-related metadata into a descriptive text that can be integrated into prompts for large language models. This allows storytellers to easily incorporate environmental context into their narratives.

## External APIs Used

The location module interacts with several external APIs:

- **IP Geolocation**: [ip-api.com](http://ip-api.com) for translating IP addresses to location information
- **Weather**: [Open-Meteo API](https://api.open-meteo.com) for current weather conditions
- **Astronomy**:
  - [Visible Planets API](https://api.visibleplanets.dev) for information about visible planets and celestial objects
  - [US Naval Observatory API](https://aa.usno.navy.mil) for solar eclipse information

## Extending the Module

To add new environmental context sources:

1. Create a new module in the `calliope.location` package
2. Define the necessary API integration functions
3. Create appropriate Pydantic models in `calliope.models.location_metadata`
4. Update the `get_location_metadata_for_ip` function in `location.py` to incorporate the new data

## Privacy Considerations

The location module processes user IP addresses to determine location. While this data is used to enhance storytelling, Calliope does not store or persist this information beyond the current session.

## Example Output

The location module might generate a context description like this for a user in New York during an autumn evening:

```
Location:
New York, New York, United States

Situation:
The date is Wednesday, October 4th, 2023.
The time is 19:45.
It is currently nighttime.
The season is autumn.
The weather is currently: Clouds generally forming or developing during the past hour.
The temperature is 12.2 degrees Celsius.
The moon is in the sky tonight.
```

This contextual information can then be used by storytelling strategies to create more immersive and situationally-aware narratives.