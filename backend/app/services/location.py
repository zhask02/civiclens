from app.schemas.location import CivicContext, LocationContext


class LocationContextService:
    """
    Converts geocoding-provider responses into CivicLens location context.

    The service contains CivicLens-specific interpretation logic while
    the GeocodingClient remains responsible only for communicating with
    the external provider.
    """

    def parse_response(
        self,
        latitude: float,
        longitude: float,
        response: dict,
    ) -> LocationContext:
        """
        Convert a raw Nominatim response into LocationContext.

        Provider fields are preserved where possible. Missing fields are
        represented as None rather than causing the entire incident
        analysis to fail.
        """

        # Nominatim places address information inside the "address" object.
        # Use an empty dictionary when that section is absent.
        address = response.get("address", {})

        # Extract native OSM information from the top-level response.
        osm_category = response.get("category")
        osm_type = response.get("type")
        osm_name = response.get("name")

        # Highway and amenity values can appear in different places
        # depending on the returned OSM object.
        osm_highway = address.get("highway")
        osm_amenity = response.get("amenity")

        # The road is generally exposed through the reverse-geocoded
        # address even when the nearest OSM object itself is not a highway.
        osm_road = address.get("road")

        # Preserve useful administrative/geographic information so the
        # eventual complaint can contain a human-readable location.
        neighbourhood = address.get("neighbourhood")
        suburb = address.get("suburb")
        city = address.get("city")
        state = address.get("state")
        postcode = address.get("postcode")
        country = address.get("country")

        # Start with no CivicLens-specific interpretation.
        civic_context = CivicContext.UNKNOWN

        # A parking OSM object is strong evidence that the incident is
        # associated with a parking area.
        if osm_type == "parking" or osm_amenity == "parking":
            civic_context = CivicContext.PARKING

        return LocationContext(
            latitude=latitude,
            longitude=longitude,
            osm_category=osm_category,
            osm_type=osm_type,
            osm_highway=osm_highway,
            osm_amenity=osm_amenity,
            osm_name=osm_name,
            osm_road=osm_road,
            neighbourhood=neighbourhood,
            suburb=suburb,
            city=city,
            state=state,
            postcode=postcode,
            country=country,
            civic_context=civic_context,
        )