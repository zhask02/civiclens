from app.schemas.location import CivicContext
from app.services.location import LocationContextService


def test_parse_highway_response():
    """Verify that a normal highway response is mapped correctly."""

    response = {
        "category": "highway",
        "type": "primary",
        "name": "GST Road",
        "address": {
            "road": "GST Road",
            "city": "Chennai",
            "state": "Tamil Nadu",
            "postcode": "600045",
            "country": "India",
        },
    }

    context = LocationContextService().parse_response(
        latitude=12.9229,
        longitude=80.1275,
        response=response,
    )

    assert context.osm_category == "highway"
    assert context.osm_type == "primary"
    assert context.osm_name == "GST Road"
    assert context.osm_road == "GST Road"
    assert context.city == "Chennai"
    assert context.civic_context == CivicContext.UNKNOWN


def test_parse_parking_response():
    """Verify that OSM parking information becomes CivicLens parking context."""

    response = {
        "category": "amenity",
        "type": "parking",
        "name": "Campus Parking",
        "amenity": "parking",
        "address": {
            "road": "Campus Road",
            "city": "Chennai",
            "state": "Tamil Nadu",
            "country": "India",
        },
    }

    context = LocationContextService().parse_response(
        latitude=12.9000,
        longitude=80.2000,
        response=response,
    )

    assert context.osm_category == "amenity"
    assert context.osm_type == "parking"
    assert context.osm_amenity == "parking"
    assert context.civic_context == CivicContext.PARKING


def test_parse_school_response():
    """Verify that a school is preserved without incorrectly calling it a campus."""

    response = {
        "category": "amenity",
        "type": "school",
        "name": "Test School",
        "address": {
            "amenity": "Test School",
            "road": "Vittal Mallya Road",
            "neighbourhood": "DS Layout",
            "suburb": "Ashokanagar",
            "city": "Bengaluru",
            "state": "Karnataka",
            "postcode": "560001",
            "country": "India",
        },
    }

    context = LocationContextService().parse_response(
        latitude=12.9716,
        longitude=77.5946,
        response=response,
    )

    assert context.osm_type == "school"
    assert context.osm_name == "Test School"
    assert context.osm_road == "Vittal Mallya Road"
    assert context.neighbourhood == "DS Layout"
    assert context.suburb == "Ashokanagar"

    # A school alone does not prove that the incident is inside a campus.
    assert context.civic_context == CivicContext.UNKNOWN


def test_parse_missing_address():
    """Verify that incomplete provider responses do not crash the parser."""

    response = {
        "category": "highway",
        "type": "residential",
        "name": "Example Road",
    }

    context = LocationContextService().parse_response(
        latitude=12.9000,
        longitude=80.2000,
        response=response,
    )

    assert context.osm_category == "highway"
    assert context.osm_type == "residential"
    assert context.osm_name == "Example Road"
    assert context.osm_road is None
    assert context.city is None


def test_parse_unknown_osm_value():
    """Verify that unfamiliar OSM vocabulary is preserved."""

    response = {
        "category": "highway",
        "type": "future_osm_value",
        "address": {},
    }

    context = LocationContextService().parse_response(
        latitude=12.9000,
        longitude=80.2000,
        response=response,
    )

    assert context.osm_type == "future_osm_value"


def test_coordinates_are_preserved():
    """Verify that the incident's original GPS coordinates remain unchanged."""

    response = {
        "category": "highway",
        "type": "primary",
        "address": {},
    }

    context = LocationContextService().parse_response(
        latitude=12.971600,
        longitude=77.594600,
        response=response,
    )

    assert context.latitude == 12.971600
    assert context.longitude == 77.594600