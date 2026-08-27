from pydantic import BaseModel, Field

class IncidentCreate(BaseModel):
    description: str = Field(
        min_length = 5,
        max_length = 1000,
        examples = ["Large pothole near the college main gate"]
    )
    latitude: float = Field(
        ge=-90,
        le=90,
        examples = [12.9716],
    )
    longitude: float = Field(
        ge=-180,
        le=180,
        examples = [77.5946],
    )
