from enum import Enum


class IncidentCategory(str, Enum):
    # Categories supported by CivicLens.
    POTHOLE = "pothole"
    STREETLIGHT = "streetlight"
    GARBAGE = "garbage"
    DRAINAGE = "drainage"
    ROAD_DAMAGE = "road_damage"
    WATER_LEAK = "water_leak"
    OTHER = "other"


class IncidentSeverity(str, Enum):
    # Describes how physically severe the detected pothole appears.
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PriorityLevel(str, Enum):
    # Describes how urgently CivicLens should prioritize the incident.
    # This is intentionally separate from IncidentSeverity because
    # severity and operational urgency are different concepts.
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentStatus(str, Enum):
    # Represents the incident's operational lifecycle.
    SUBMITTED = "submitted"
    ANALYZED = "analyzed"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"