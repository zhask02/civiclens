import json

from app.clients.geocoding import GeocodingClient
from app.clients.redis import redis_client
from app.schemas.location import LocationContext
from app.services.location_context import CivicContextInterpreter


class LocationContextService:
    """
    Coordinates location lookups for CivicLens.

    Redis is used as a cache so repeated reports near the same coordinates
    do not repeatedly call the external Nominatim service.
    """

    CACHE_PREFIX = "location:reverse:"
    CACHE_TTL_SECONDS = 24 * 60 * 60

    def __init__(
        self,
        geocoding_client: GeocodingClient | None = None,
    ) -> None:
        # Allow tests to inject a fake geocoding client without making
        # real network requests.
        self.geocoding_client = geocoding_client or GeocodingClient()

    @staticmethod
    def _normalize_coordinates(
        latitude: float,
        longitude: float,
    ) -> tuple[float, float]:
        """
        Normalize GPS coordinates before creating a cache key.

        Five decimal places correspond to roughly metre-level latitude
        precision, which avoids creating separate cache entries for tiny
        GPS variations while keeping nearby roads distinct.
        """

        return round(latitude, 5), round(longitude, 5)

    def _build_cache_key(
        self,
        latitude: float,
        longitude: float,
    ) -> str:
        """
        Build a deterministic Redis key for a geographic location.
        """

        latitude, longitude = self._normalize_coordinates(
            latitude,
            longitude,
        )

        return f"{self.CACHE_PREFIX}{latitude}:{longitude}"

    def get_context(
        self,
        latitude: float,
        longitude: float,
    ) -> LocationContext:
        """
        Retrieve geographic context using Redis caching.

        Cache hit:
            Return the cached provider response.

        Cache miss:
            Query Nominatim, cache its response, then parse it into
            the CivicLens location schema.
        """

        cache_key = self._build_cache_key(
            latitude,
            longitude,
        )

        # Check Redis before contacting the external provider.
        cached_response = redis_client.get(cache_key)

        if cached_response is not None:
            try:
                # Redis normally returns a string because our client uses
                # decode_responses=True, but support bytes defensively as well.
                if isinstance(cached_response, bytes):
                    cached_response = cached_response.decode("utf-8")

                response = json.loads(cached_response)

                # Only use the cache when it contains a JSON object suitable
                # for the location parser.
                if isinstance(response, dict):
                    return self.parse_response(
                        latitude=latitude,
                        longitude=longitude,
                        response=response,
                    )

            except (UnicodeDecodeError, json.JSONDecodeError):
                # A corrupted cache entry should never prevent a fresh lookup.
                # We simply treat it as a cache miss and refresh the data below.
                pass

        # No cached result exists, so contact Nominatim.
        response = self.geocoding_client.reverse(
            latitude=latitude,
            longitude=longitude,
        )

        # Cache the raw provider response rather than our interpreted
        # schema so we retain the original geographic evidence.
        redis_client.setex(
            cache_key,
            self.CACHE_TTL_SECONDS,
            json.dumps(response),
        )

        return self.parse_response(
            latitude=latitude,
            longitude=longitude,
            response=response,
        )

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
        # Nominatim may expose amenity information either at the top level
        # or inside the nested address object, depending on the response.
        osm_amenity = response.get("amenity") or address.get("amenity")

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

        # Let the dedicated interpreter translate OSM evidence into a
        # CivicLens-specific operational context.
        #
        # The parser remains responsible for extracting provider data,
        # while CivicContextInterpreter owns CivicLens's business rules.
        civic_context = CivicContextInterpreter.interpret(
            osm_type=osm_type,
            osm_amenity=osm_amenity,
        )

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