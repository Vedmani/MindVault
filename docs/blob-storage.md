# Blob Storage

MindVault saves tweet media to MinIO via an S3-compatible client.

## Configuration

Set these values in `.env`:

```env
BLOB_STORAGE_PROVIDER=minio
BLOB_STORAGE_ENDPOINT_URL=http://localhost:9000
BLOB_STORAGE_ACCESS_KEY=minioadmin
BLOB_STORAGE_SECRET_KEY=minioadmin
BLOB_STORAGE_BUCKET_NAME=mindvault-media
BLOB_STORAGE_REGION=us-east-1
BLOB_STORAGE_ADDRESSING_STYLE=path
BLOB_STORAGE_VERIFY_SSL=false
BLOB_STORAGE_AUTO_CREATE_BUCKET=true
```

## Docker compose usage

`docker-compose.yml` includes:

- `mongodb`
- `minio`

Start services:

```sh
docker compose up -d
```

## Deprecation timeline

- Filesystem media path (`download_tweet_media(...)`) is deprecated and will be
  removed in a follow-up release.
