"""MinIO artifact persistence for training flows."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

import boto3
from botocore.client import Config

@dataclass(frozen=True)
class MinioArtifactStore:
    """S3-compatible artifact store configured for the project's MinIO service."""

    # MinIO Service configuration
    endpoint: str
    bucket: str
    access_key: str
    secret_key: str

    @classmethod
    def _environment(cls) -> "MinioArtifactStore":
        endpoint = os.getenv("MINIO_ENDPOINT", "minio:9000").strip()
        bucket = os.getenv("MINIO_BUCKET", "paylater-models").strip()
        access_key = (
            os.getenv("MINIO_ACCESS_KEY") or os.getenv("MINIO_ROOT_USER") or "").strip()
        secret_key = (os.getenv("MINIO_SECRET_KEY") or os.getenv("MINIO_ROOT_PASSWORD") or "").strip()
        missing = [
            name
            for name, value in (
                ("MINIO_ACCESS_KEY or MINIO_ROOT_USER", access_key),
                ("MINIO_SECRET_KEY or MINIO_ROOT_PASSWORD", secret_key),
            )
            if not value
        ]
        if missing:
            raise RuntimeError(
                f"MinIO artifact configuration is incomplete: {', '.join(missing)}"
            )
        if "://" not in endpoint:
            endpoint = f"http://{endpoint}"
        return cls(endpoint, bucket, access_key, secret_key)

    def _client(self):
        return boto3.client(
            "s3",
            endpoint_url=self.endpoint,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name="us-east-1",
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
            ),
        )

    def ensure_bucket(self) -> None:
        client = self._client()
        try:
            client.head_bucket(Bucket=self.bucket)
        except client.exceptions.ClientError as exc:
            status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if status != 404:
                raise RuntimeError(
                    f"Unable to access MinIO bucket '{self.bucket}'"
                ) from exc
            try:
                client.create_bucket(Bucket=self.bucket)
            except Exception as create_error:
                raise RuntimeError(
                    f"Unable to create MinIO bucket '{self.bucket}'"
                ) from create_error

    def upload_file(self, source: Path, object_key: str) -> str:
        """Upload one temporary artifact and return its MinIO URI."""
        if not source.is_file():
            raise FileNotFoundError(f"Artifact file does not exist: {source}")
        try:
            self.ensure_bucket()
            self._client().upload_file(str(source), self.bucket, object_key)
        except Exception as exc:
            raise RuntimeError(
                f"Unable to upload artifact to MinIO: {self.bucket}/{object_key}"
            ) from exc
        return f"s3://{self.bucket}/{object_key}"

    def upload_stream(self, stream: BinaryIO, object_key: str) -> str:
        """Upload a binary stream and return its MinIO URI."""
        try:
            self.ensure_bucket()
            self._client().upload_fileobj(stream, self.bucket, object_key)
        except Exception as exc:
            raise RuntimeError(
                f"Unable to upload artifact to MinIO: {self.bucket}/{object_key}"
            ) from exc
        return f"s3://{self.bucket}/{object_key}"
