import hashlib
import structlog
from io import BytesIO
from minio import Minio
from minio.error import S3Error

from app.core.config import get_settings

settings = get_settings()
logger = structlog.get_logger()


def _get_client() -> Minio:
    return Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=False,
    )


def ensure_bucket(client: Minio | None = None) -> None:
    client = client or _get_client()
    if not client.bucket_exists(settings.MINIO_BUCKET_RAW):
        client.make_bucket(settings.MINIO_BUCKET_RAW)
        logger.info("bucket_created", bucket=settings.MINIO_BUCKET_RAW)


def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def upload_raw_artifact(
    case_id: str,
    device_id: str | None,
    filename: str,
    data: bytes,
) -> tuple[str, str]:
    sha256 = compute_sha256(data)
    storage_path = f"cases/{case_id}/raw/{sha256}/{filename}"

    client = _get_client()
    ensure_bucket(client)

    client.put_object(
        settings.MINIO_BUCKET_RAW,
        storage_path,
        BytesIO(data),
        length=len(data),
        content_type="application/octet-stream",
    )

    logger.info(
        "artifact_uploaded",
        case_id=case_id,
        filename=filename,
        sha256=sha256,
        storage_path=storage_path,
    )
    return sha256, storage_path


def download_raw_artifact(storage_path: str) -> bytes:
    client = _get_client()
    response = client.get_object(settings.MINIO_BUCKET_RAW, storage_path)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def verify_artifact_integrity(storage_path: str, expected_sha256: str) -> bool:
    data = download_raw_artifact(storage_path)
    actual_sha256 = compute_sha256(data)
    if actual_sha256 != expected_sha256:
        logger.error(
            "integrity_check_failed",
            storage_path=storage_path,
            expected=expected_sha256,
            actual=actual_sha256,
        )
        return False
    return True
