import httpx


class GeocodingClient:
    """
    Handles communication with the external geocoding provider.

    A persistent HTTP client is used so TCP/TLS connections can be
    reused across requests instead of creating a new connection for
    every reverse-geocoding lookup.
    """

    BASE_URL = "https://nominatim.openstreetmap.org/reverse"

    def __init__(self) -> None:
        # Identify CivicLens to the public Nominatim service.
        # Nominatim requires an identifiable User-Agent.
        self.headers = {
            "User-Agent": "CivicLens/1.0",
        }

        # Keep one HTTP client for the lifetime of this geocoding
        # client so httpx can reuse connections through its connection pool.
        self.client = httpx.Client(
            headers=self.headers,
            timeout=10.0,
        )

    def reverse(
        self,
        latitude: float,
        longitude: float,
    ) -> dict:
        """
        Reverse-geocode coordinates using Nominatim.

        The raw provider response is returned so that the service layer
        can decide which fields are meaningful to CivicLens.
        """

        params = {
            "lat": latitude,
            "lon": longitude,
            "format": "jsonv2",
            "addressdetails": 1,
            "zoom": 18,
            "accept-language": "en",
        }

        try:
            # Reuse the persistent HTTP client's connection pool.
            response = self.client.get(
                self.BASE_URL,
                params=params,
            )

            # Treat non-successful HTTP responses as provider failures.
            response.raise_for_status()

            return response.json()

        except httpx.HTTPError as exc:
            # Keep provider-specific HTTP exceptions inside the
            # client boundary so the service layer remains provider-agnostic.
            raise RuntimeError(
                "Geocoding provider request failed"
            ) from exc

    def close(self) -> None:
        """
        Release the HTTP client's network resources.
        """

        # Explicitly close the connection pool when the client is no longer used.
        self.client.close()