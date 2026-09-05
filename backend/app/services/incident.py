from app.enums.incident import IncidentStatus


ALLOWED_STATUS_TRANSITIONS = {
    IncidentStatus.SUBMITTED: [IncidentStatus.ANALYZED],
    IncidentStatus.ANALYZED: [IncidentStatus.ASSIGNED],
    IncidentStatus.ASSIGNED: [IncidentStatus.IN_PROGRESS],
    IncidentStatus.IN_PROGRESS: [IncidentStatus.RESOLVED],
    IncidentStatus.RESOLVED: [],
}


def can_transition_status(
    current_status: IncidentStatus,
    new_status: IncidentStatus,
) -> bool:
    allowed_statuses = ALLOWED_STATUS_TRANSITIONS[current_status]

    return new_status in allowed_statuses