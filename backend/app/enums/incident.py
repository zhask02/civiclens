from enum import Enum

class IncidentCategory(str, Enum):
    POTHOLE = "pothole"
    STREETLIGHT = "streetlight"
    GARBAGE = "garbage"
    DRAINAGE = "drainage"
    ROAD_DAMAGE = "road_damage"
    WATER_LEAK = "water_leak"
    OTHER = "other"

class IncidentSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class IncidentStatus(str, Enum):
    SUBMITTED = "submitted"
    ANALYZED = "analyzed"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"