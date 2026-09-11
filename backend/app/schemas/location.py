from enum import Enum

from pydantic import BaseModel


class CivicContext(str, Enum):
    """
    CivicLens-specific interpretation of a location.

    These values describe useful reporting contexts while remaining
    separate from OpenStreetMap's own vocabulary.
    """

    CAMPUS = "campus"
    PARKING = "parking"
    UNKNOWN = "unknown"


class LocationContext(BaseModel):
    """
    Structured geographic information associated with an incident.

    OSM-derived fields are kept close to the provider's vocabulary so
    CivicLens preserves useful geographic evidence instead of forcing
    everything into a small custom taxonomy.
    """

    latitude: float
    longitude: float

    # Nominatim's broad classification of the returned OSM object.
    # Examples include "highway", "amenity", "place", etc.
    osm_category: str | None = None

    # Nominatim's specific object type.
    # Examples include "school", "parking", "residential", etc.
    osm_type: str | None = None

    # Native OSM highway classification when one is available.
    # We keep this as a string because OSM's vocabulary can evolve.
    osm_highway: str | None = None

    # Native OSM amenity classification when available.
    # For example: "parking", "school", "hospital".
    osm_amenity: str | None = None

    # Human-readable name of the mapped OSM object.
    osm_name: str | None = None

    # Road associated with the reported coordinates.
    osm_road: str | None = None

    # Administrative/geographic address information useful for
    # producing a human-readable complaint.
    neighbourhood: str | None = None
    suburb: str | None = None
    city: str | None = None
    state: str | None = None
    postcode: str | None = None
    country: str | None = None

    # CivicLens-specific interpretation of the location.
    civic_context: CivicContext = CivicContext.UNKNOWN