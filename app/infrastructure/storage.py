"""Azure Blob Storage utilities for file management."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from azure.storage.blob import BlobServiceClient, ContentSettings

from app.config import get_settings


@lru_cache
def _get_blob_service_client() -> BlobServiceClient:
    settings = get_settings()
    if not settings.azure_storage_connection_string:
        msg = "Azure storage connection string is not configured"
        raise RuntimeError(msg)
    return BlobServiceClient.from_connection_string(
        settings.azure_storage_connection_string
    )


@lru_cache
def _get_container_name() -> str:
    settings = get_settings()
    if not settings.azure_storage_container_name:
        msg = "Azure storage container name is not configured"
        raise RuntimeError(msg)
    return settings.azure_storage_container_name


@lru_cache
def _get_container_client():
    service_client = _get_blob_service_client()
    container_name = _get_container_name()
    try:
        service_client.create_container(container_name)
    except ResourceExistsError:
        pass
    return service_client.get_container_client(container_name)


def upload_blob(
    blob_path: str,
    data: bytes,
    *,
    content_type: Optional[str] = None,
) -> None:
    """Upload ``data`` to the configured storage container at ``blob_path``."""

    container_client = _get_container_client()
    blob_client = container_client.get_blob_client(blob_path)
    content_settings = None
    if content_type is not None:
        content_settings = ContentSettings(content_type=content_type)
    blob_client.upload_blob(
        data,
        overwrite=True,
        content_settings=content_settings,
    )


def delete_blob(blob_path: str) -> None:
    """Delete the blob located at ``blob_path`` if it exists."""

    container_client = _get_container_client()
    blob_client = container_client.get_blob_client(blob_path)
    try:
        blob_client.delete_blob()
    except ResourceNotFoundError:
        return


def download_blob_to_path(blob_path: str, destination: Path) -> Path:
    """Download the blob located at ``blob_path`` into ``destination``."""

    container_client = _get_container_client()
    blob_client = container_client.get_blob_client(blob_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        stream = blob_client.download_blob()
    except ResourceNotFoundError as exc:  # pragma: no cover - network edge case
        raise FileNotFoundError(blob_path) from exc
    data = stream.readall()
    destination.write_bytes(data)
    return destination


__all__ = [
    "upload_blob",
    "delete_blob",
    "download_blob_to_path",
]
