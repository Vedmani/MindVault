import os
import unittest

os.environ.setdefault("TWITTER_CT0", "test-ct0")
os.environ.setdefault("TWITTER_AUTH_TOKEN", "test-auth")
os.environ.setdefault("VALIDATE_EXTERNAL_SERVICES_ON_STARTUP", "false")

from mindvault.core.config import Settings


class BlobStorageConfigTests(unittest.TestCase):
    def _settings(self, **overrides) -> Settings:
        return Settings(
            _env_file=None,
            validate_on_startup=False,
            twitter_ct0="test-ct0",
            twitter_auth_token="test-auth",
            **overrides,
        )

    def test_generic_values_override_minio_defaults(self) -> None:
        settings = self._settings(
            blob_storage_provider="minio",
            blob_storage_endpoint_url="http://generic-endpoint",
            blob_storage_access_key="generic-access",
            blob_storage_secret_key="generic-secret",
            blob_storage_bucket_name="generic-bucket",
            blob_storage_region="eu-west-1",
        )

        resolved = settings.get_blob_storage_connection()

        self.assertEqual(resolved.provider, "minio")
        self.assertEqual(resolved.endpoint_url, "http://generic-endpoint")
        self.assertEqual(resolved.access_key, "generic-access")
        self.assertEqual(resolved.secret_key, "generic-secret")
        self.assertEqual(resolved.bucket_name, "generic-bucket")
        self.assertEqual(resolved.region, "eu-west-1")

    def test_minio_provider_uses_defaults(self) -> None:
        settings = self._settings(blob_storage_provider="minio")

        resolved = settings.get_blob_storage_connection()

        self.assertEqual(resolved.provider, "minio")
        self.assertEqual(resolved.endpoint_url, "http://localhost:9000")
        self.assertEqual(resolved.access_key, "minioadmin")
        self.assertEqual(resolved.secret_key, "minioadmin")
        self.assertEqual(resolved.bucket_name, "mindvault-media")
        self.assertEqual(resolved.addressing_style, "path")

    def test_bucket_name_override_argument_takes_precedence(self) -> None:
        settings = self._settings(blob_storage_provider="minio")
        resolved = settings.get_blob_storage_connection(bucket_name="override-bucket")
        self.assertEqual(resolved.bucket_name, "override-bucket")

    def test_invalid_provider_raises(self) -> None:
        settings = self._settings(blob_storage_provider="minio")
        with self.assertRaises(ValueError):
            settings.get_blob_storage_connection(provider="unsupported-provider")


if __name__ == "__main__":
    unittest.main()
