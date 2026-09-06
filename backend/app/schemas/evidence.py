from datetime import datetime

from pydantic import BaseModel


class EvidenceCreate(BaseModel):
    storage_path: str
    file_type: str


class EvidenceResponse(BaseModel):
    id: int
    incident_id: int
    storage_path: str
    file_type: str
    created_at: datetime

    class Config:
        from_attributes = True

class EvidenceURLResponse(BaseModel):
    url: str