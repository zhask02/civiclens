from app.schemas.location import CivicContext


class CivicContextInterpreter:
    """
    Interprets raw OpenStreetMap information into CivicLens-specific
    location contexts.

    OSM remains the source of geographic vocabulary. This class only
    adds CivicLens's own operational interpretation on top of it.
    """

    # These OSM object types provide strong enough evidence that the
    # location is associated with a campus/institutional environment.
    CAMPUS_TYPES = {
        "college",
        "university",
    }

    @classmethod
    def interpret(
        cls,
        osm_type: str | None,
        osm_amenity: str | None,
    ) -> CivicContext:
        """
        Convert OSM classifications into a CivicLens civic context.

        We deliberately require explicit OSM evidence rather than
        guessing a campus from a place name or GPS coordinates.
        """

        # Parking is explicitly represented by OSM and is useful for
        # distinguishing parking-area incidents operationally.
        if osm_type == "parking" or osm_amenity == "parking":
            return CivicContext.PARKING

        # Educational OSM objects are strong evidence of a campus-like
        # environment. We keep the original OSM type separately.
        if osm_type in cls.CAMPUS_TYPES:
            return CivicContext.CAMPUS

        # If OSM does not provide enough evidence for a CivicLens-specific
        # interpretation, preserve the uncertainty instead of guessing.
        return CivicContext.UNKNOWN