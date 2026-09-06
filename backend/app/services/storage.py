import uuid

from app.clients.supabase import supabase


BUCKET_NAME = "civiclens-evidence"


def upload_evidence_file(
    incident_id: int,
    file_bytes: bytes,
    file_extension: str,
    content_type: str,
) -> str:
    storage_path = (
        f"incidents/{incident_id}/{uuid.uuid4()}.{file_extension}"
    )

    supabase.storage.from_(BUCKET_NAME).upload(
        storage_path,
        file_bytes,
        {
            "content-type": content_type,
        },
    )

    return storage_path


def delete_evidence_file(storage_path: str) -> None:
    supabase.storage.from_(BUCKET_NAME).remove(
        [storage_path]
    )


def create_evidence_signed_url(
    storage_path: str,
    expires_in: int = 3600,
) -> str:
    response = (
        supabase.storage
        .from_(BUCKET_NAME)
        .create_signed_url(
            storage_path,
            expires_in,
        )
    )

    return response["signedURL"]