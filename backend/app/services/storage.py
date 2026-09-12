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

def download_evidence_file(storage_path: str) -> bytes:
    """
    Download an evidence image from Supabase Storage.

    The analysis pipeline works with raw image bytes so that the
    detector does not need to know anything about Supabase or URLs.
    """

    # Ask the private evidence bucket for the stored file.
    response = (
        supabase.storage
        .from_(BUCKET_NAME)
        .download(storage_path)
    )

    return response