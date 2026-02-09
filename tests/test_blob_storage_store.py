import os
import unittest
from unittest.mock import AsyncMock, patch

from botocore.exceptions import ClientError

os.environ.setdefault("TWITTER_CT0", "test-ct0")
os.environ.setdefault("TWITTER_AUTH_TOKEN", "test-auth")
os.environ.setdefault("VALIDATE_EXTERNAL_SERVICES_ON_STARTUP", "false")

from mindvault.bookmarks.twitter.download_tweet_media_object_storage import (
    _check_object_exists,
    _ensure_bucket_exists,
    _upload_stream_to_s3_compatible,
    build_s3_uri,
)
from mindvault.bookmarks.twitter.extract import ExtractedMedia, ExtractedMediaList
from mindvault.bookmarks.twitter.media_download import download_media
from mindvault.core.config import BlobStorageConnection


async def _stream_chunks(chunks):
    for chunk in chunks:
        yield chunk


def _make_head_bucket_error(code: str, status_code: int) -> ClientError:
    return ClientError(
        error_response={
            "Error": {"Code": code, "Message": "error"},
            "ResponseMetadata": {"HTTPStatusCode": status_code},
        },
        operation_name="HeadBucket",
    )


class BlobStorageStoreTests(unittest.IsolatedAsyncioTestCase):
    async def test_ensure_bucket_exists_creates_bucket_when_missing(self) -> None:
        connection = BlobStorageConnection(
            provider="minio",
            endpoint_url="http://localhost:9000",
            access_key="x",
            secret_key="y",
            bucket_name="mindvault-media",
            region="us-east-1",
            addressing_style="path",
            verify_ssl=False,
            auto_create_bucket=True,
        )
        s3_client = AsyncMock()
        s3_client.head_bucket.side_effect = _make_head_bucket_error("404", 404)

        await _ensure_bucket_exists(s3_client, connection)

        s3_client.create_bucket.assert_awaited_once_with(Bucket="mindvault-media")

    async def test_ensure_bucket_exists_raises_when_auto_create_disabled(self) -> None:
        connection = BlobStorageConnection(
            provider="minio",
            endpoint_url="http://localhost:9000",
            access_key="x",
            secret_key="y",
            bucket_name="mindvault-media",
            region="us-east-1",
            addressing_style="path",
            verify_ssl=False,
            auto_create_bucket=False,
        )
        s3_client = AsyncMock()
        s3_client.head_bucket.side_effect = _make_head_bucket_error("NoSuchBucket", 404)

        with self.assertRaises(ConnectionError):
            await _ensure_bucket_exists(s3_client, connection)

    async def test_ensure_bucket_exists_does_not_create_bucket_for_non_missing_errors(self) -> None:
        connection = BlobStorageConnection(
            provider="minio",
            endpoint_url="http://localhost:9000",
            access_key="x",
            secret_key="y",
            bucket_name="mindvault-media",
            region="us-east-1",
            addressing_style="path",
            verify_ssl=False,
            auto_create_bucket=True,
        )
        s3_client = AsyncMock()
        s3_client.head_bucket.side_effect = _make_head_bucket_error("AccessDenied", 403)

        with self.assertRaises(ClientError):
            await _ensure_bucket_exists(s3_client, connection)

        s3_client.create_bucket.assert_not_awaited()

    async def test_check_object_exists_respects_content_length(self) -> None:
        s3_client = AsyncMock()
        s3_client.head_object.return_value = {"ContentLength": 128}

        self.assertTrue(await _check_object_exists(s3_client, "bucket", "key"))

        s3_client.head_object.return_value = {"ContentLength": 0}
        self.assertFalse(await _check_object_exists(s3_client, "bucket", "key"))

    async def test_upload_stream_aborts_empty_file(self) -> None:
        s3_client = AsyncMock()
        s3_client.create_multipart_upload.return_value = {"UploadId": "upload-1"}

        success = await _upload_stream_to_s3_compatible(
            s3_client=s3_client,
            stream=_stream_chunks([]),
            bucket_name="bucket",
            key="tweet/media.jpg",
        )

        self.assertFalse(success)
        s3_client.abort_multipart_upload.assert_awaited_once()

    async def test_upload_stream_completes_for_non_empty_file(self) -> None:
        s3_client = AsyncMock()
        s3_client.create_multipart_upload.return_value = {"UploadId": "upload-1"}
        s3_client.upload_part.return_value = {"ETag": "etag-1"}

        success = await _upload_stream_to_s3_compatible(
            s3_client=s3_client,
            stream=_stream_chunks([b"abc"]),
            bucket_name="bucket",
            key="tweet/media.jpg",
        )

        self.assertTrue(success)
        s3_client.complete_multipart_upload.assert_awaited_once()

    async def test_download_media_retries_after_transient_store_failure(self) -> None:
        item = ExtractedMedia(
            tweet_id="123",
            media_id="media-1",
            media_url="https://example.com/image.jpg",
            media_type="image",
        )
        media_list = ExtractedMediaList(media=[item])

        class FlakyStore:
            def __init__(self) -> None:
                self.calls = 0

            async def prepare(self) -> None:
                return None

            def get_location(self, _item):
                return "s3://mindvault-media/123/media-1.jpg"

            async def exists(self, _item) -> bool:
                return False

            async def save(self, item, stream, *, content_type=None):
                self.calls += 1
                async for _ in stream:
                    break
                if self.calls == 1:
                    raise IOError("transient")
                return "s3://mindvault-media/123/media-1.jpg"

        class DummyClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return None

        store = FlakyStore()

        with patch(
            "mindvault.bookmarks.twitter.media_download._create_http_client",
            AsyncMock(return_value=DummyClient()),
        ), patch(
            "mindvault.bookmarks.twitter.media_download.download_media_stream",
            side_effect=lambda client, url, chunk_size: _stream_chunks([b"data"]),
        ):
            result = await download_media(
                media_list=media_list,
                store=store,
                max_retries=1,
                retry_delay=0.0,
                skip_existing=False,
                progress_desc="test",
            )

        self.assertEqual(store.calls, 2)
        self.assertEqual(result["123"], ["s3://mindvault-media/123/media-1.jpg"])


class BlobStorageUriTests(unittest.TestCase):
    def test_s3_uri_format(self) -> None:
        self.assertEqual(
            build_s3_uri("mindvault-media", "123/media-1.jpg"),
            "s3://mindvault-media/123/media-1.jpg",
        )


if __name__ == "__main__":
    unittest.main()
