from enum import Enum

from pydantic import BaseModel


class RoadType(str, Enum):
    """
    Broad categories describing the road or area around an incident.

    This is contextual information. It does NOT describe how physically
    severe the pothole itself is.
    """

    HIGHWAY = "highway"
    ARTERIAL = "arterial"
    RESIDENTIAL = "residential"
    PARKING = "parking"
    CAMPUS = "campus"
    UNKNOWN = "unknown"


class LocationContext(BaseModel):
    """
    Geographic context associated with an incident.

    The road type can initially be supplied manually. Later, a
    geospatial service can determine it automatically from GPS
    coordinates without changing this model.
    """

    latitude: float
    longitude: float
    road_type: RoadType = RoadType.UNKNOWN