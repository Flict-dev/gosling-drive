from botocore.client import Config
from botocore.exceptions import ClientError
import boto3

from app.core.config import settings


class S3Storage:
    def __init__(self) -> None:
        self.bucket = settings.s3_bucket_name
        self._internal = self._client(settings.s3_endpoint_url)
        self._public = self._client(settings.s3_public_endpoint_url)

    @staticmethod
    def _client(endpoint_url: str):
        return boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )

    def ensure_bucket(self) -> None:
        try:
            self._internal.head_bucket(Bucket=self.bucket)
        except ClientError:
            self._internal.create_bucket(Bucket=self.bucket)
        try:
            self._internal.put_bucket_cors(
                Bucket=self.bucket,
                CORSConfiguration={
                    "CORSRules": [
                        {
                            "AllowedOrigins": [
                                "http://localhost:8000",
                                "http://127.0.0.1:8000",
                            ],
                            "AllowedMethods": ["GET", "PUT", "POST", "DELETE", "HEAD"],
                            "AllowedHeaders": ["*"],
                            "ExposeHeaders": ["ETag", "x-amz-request-id"],
                            "MaxAgeSeconds": 3000,
                        }
                    ]
                },
            )
        except ClientError:
            pass

    def create_multipart_upload(self, object_key: str, content_type: str) -> str:
        response = self._internal.create_multipart_upload(
            Bucket=self.bucket,
            Key=object_key,
            ContentType=content_type,
        )
        return response["UploadId"]

    def presign_upload_part(self, object_key: str, upload_id: str, part_number: int) -> str:
        return self._public.generate_presigned_url(
            ClientMethod="upload_part",
            Params={
                "Bucket": self.bucket,
                "Key": object_key,
                "UploadId": upload_id,
                "PartNumber": part_number,
            },
            ExpiresIn=settings.s3_presigned_expire_seconds,
            HttpMethod="PUT",
        )

    def complete_multipart_upload(
        self,
        object_key: str,
        upload_id: str,
        parts: list[dict],
    ) -> str | None:
        normalized_parts = [
            {"PartNumber": part["part_number"], "ETag": normalize_etag(part["etag"])}
            for part in sorted(parts, key=lambda item: item["part_number"])
        ]
        response = self._internal.complete_multipart_upload(
            Bucket=self.bucket,
            Key=object_key,
            UploadId=upload_id,
            MultipartUpload={"Parts": normalized_parts},
        )
        return response.get("ETag")

    def abort_multipart_upload(self, object_key: str, upload_id: str) -> None:
        self._internal.abort_multipart_upload(
            Bucket=self.bucket,
            Key=object_key,
            UploadId=upload_id,
        )

    def presign_download(self, object_key: str, filename: str | None = None) -> str:
        params = {"Bucket": self.bucket, "Key": object_key}
        if filename:
            params["ResponseContentDisposition"] = f'attachment; filename="{filename}"'
        return self._public.generate_presigned_url(
            ClientMethod="get_object",
            Params=params,
            ExpiresIn=settings.s3_presigned_expire_seconds,
            HttpMethod="GET",
        )

    def delete_object(self, object_key: str) -> None:
        self._internal.delete_object(Bucket=self.bucket, Key=object_key)


def normalize_etag(etag: str) -> str:
    stripped = etag.strip()
    if stripped.startswith('"') and stripped.endswith('"'):
        return stripped
    return f'"{stripped}"'


storage = S3Storage()
