from app.schemas.location import LocationContext, RoadType


class LocationContextService:
    """
    Provides geographic context for an incident.

    The service is intentionally separated from the Pydantic schema.
    The schema defines the shape of the data, while this service defines
    how CivicLens obtains that data.

    For now, road type defaults to UNKNOWN. A geospatial provider can
    be connected later without changing the rest of the application.
    """

    def get_context(
        self,
        latitude: float,
        longitude: float,
    ) -> LocationContext:
        """
        Return geographic context for the supplied coordinates.

        The initial implementation does not call an external API yet.
        Keeping that boundary here allows us to add OpenStreetMap or
        another GIS provider later without changing callers.
        """

        return LocationContext(
            latitude=latitude,
            longitude=longitude,
            road_type=RoadType.UNKNOWN,
        )