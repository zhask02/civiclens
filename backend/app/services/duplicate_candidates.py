from datetime import datetime, timedelta, timezone
from math import cos, radians, pi

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums.incident import IncidentCategory
from app.models.incident import Incident
from app.services.duplicate import haversine_distance_meters


class DuplicateCandidateService:
    """
    Retrieves existing incidents that are plausible duplicate candidates.

    This service deliberately does not decide whether two incidents are
    duplicates. Its responsibility is only to reduce the database search
    space before DuplicateService performs the actual comparison.
    """

    # A pothole reported more than 100 m away is outside our current
    # duplicate-detection geographic search radius.
    MAX_DISTANCE_METERS = 100.0

    # Reports older than 72 hours are outside our current duplicate-
    # detection time window.
    MAX_TIME_HOURS = 72.0

    # Approximate Earth radius used to convert metres into latitude/
    # longitude ranges for the inexpensive database pre-filter.
    EARTH_RADIUS_METERS = 6_371_000.0

    def find_candidates(
        self,
        db: Session,
        *,
        latitude: float,
        longitude: float,
        created_at: datetime,
        exclude_incident_id: int | None = None,
    ) -> list[Incident]:
        """
        Find recent pothole incidents within the configured search radius.

        The database first applies a cheap bounding-box filter. We then
        calculate the exact Haversine distance in Python because the
        current database stores coordinates as ordinary Float columns
        rather than using a spatial/PostGIS type.
        """

        # Convert the search radius from metres to degrees of latitude.
        # The trigonometric functions use radians, so we explicitly
        # convert the resulting angular distance back into degrees
        # before comparing it with latitude/longitude columns.
        latitude_delta = (
            self.MAX_DISTANCE_METERS
            / self.EARTH_RADIUS_METERS
        ) * (180.0 / pi)

        # Longitude degrees represent a smaller physical distance as
        # latitude increases. Compensate for that using the cosine of
        # the incident latitude.
        longitude_scale = max(abs(cos(radians(latitude))), 1e-12)

        longitude_delta = (
            self.MAX_DISTANCE_METERS
            / (self.EARTH_RADIUS_METERS * longitude_scale)
        ) * (180.0 / pi)

        # The Incident model currently stores UTC timestamps as naive
        # datetimes via datetime.utcnow(). Normalize an incoming aware
        # timestamp to the same representation before querying the DB.
        if created_at.tzinfo is not None:
            created_at = created_at.astimezone(timezone.utc).replace(
                tzinfo=None
            )

        # Only recent incidents can currently be duplicates.
        cutoff_time = created_at - timedelta(
            hours=self.MAX_TIME_HOURS
        )

        statement = select(Incident).where(
            # CivicLens v1 is pothole-only, so unrelated incident
            # categories should never enter the duplicate comparison.
            Incident.category == IncidentCategory.POTHOLE,

            # Restrict candidates to the configured recent time window.
            Incident.created_at >= cutoff_time,

            # Cheap geographic bounding-box filter. This is intentionally
            # broader than the exact circle; Haversine below performs the
            # final distance check.
            Incident.latitude >= latitude - latitude_delta,
            Incident.latitude <= latitude + latitude_delta,
            Incident.longitude >= longitude - longitude_delta,
            Incident.longitude <= longitude + longitude_delta,
        )

        # When checking an already-persisted incident, prevent that same
        # row from being returned as its own duplicate candidate.
        if exclude_incident_id is not None:
            statement = statement.where(
                Incident.id != exclude_incident_id
            )

        # Fetch only rows surviving the inexpensive database filters.
        incidents = db.scalars(statement).all()

        candidates = []

        for incident in incidents:
            # The bounding box is only an approximation. Two points can
            # both fit inside the box while still being more than 100 m
            # apart, so perform the exact geographic calculation here.
            distance = haversine_distance_meters(
                latitude,
                longitude,
                incident.latitude,
                incident.longitude,
            )

            if distance <= self.MAX_DISTANCE_METERS:
                candidates.append(incident)

        # Return the newest candidates first so the most recent reports
        # are considered first by the later duplicate-analysis stage.
        candidates.sort(
            key=lambda incident: incident.created_at,
            reverse=True,
        )

        return candidates