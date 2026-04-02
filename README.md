# CeramiCraft Notification Microservice

Push notification microservice for the CeramiCraft e-commerce system. It provides an HTTP API for device token registration and a gRPC RPC for sending push notifications via FCM.

## Features

- **HTTP API**: Register and update device push tokens (`FCM`, etc.).
- **gRPC API**: Send push notifications to specific users.
- **Secure**: Encrypts notification payloads using AES-256-GCM before sending.
- **Asynchronous**: Built with FastAPI, `grpc.aio`, and SQLAlchemy 2.0 async support.
- **Containerized**: Dockerfile and docker-compose setup for easy deployment.

## Tech Stack

- Python 3.12, `uv`
- FastAPI, Uvicorn
- `grpc.aio`
- PostgreSQL, SQLAlchemy (asyncio), `asyncpg`
- `firebase-admin` for FCM
- `cryptography` for encryption
- `typer` for CLI commands
- `pytest`, `testcontainers` for testing

## HTTP API

### Authentication

All protected endpoints require the `X-Original-User-ID` header, injected by the API Gateway after JWT verification (consistent with Go microservices). Direct callers without a gateway must supply this header manually.

### Endpoints

#### `GET /notification-ms/v1/ping`

Health check. Returns `{"status": "ok"}`.

#### `POST /notification-ms/v1/push-token`

Register or update a device's FCM push token. Each call rotates the AES key (key rotation on re-registration is intentional).

**Required header:**
```
X-Original-User-ID: <integer user ID>
```

**Request body:**
```json
{
  "device_id": "string",
  "fcm_token": "string"
}
```

**Response `200`:**
```json
{
  "aes_key": "<Base64-encoded 32-byte AES-256 key>"
}
```

The client must persist `aes_key` securely (e.g. device Keychain / SecureStore). Incoming push payloads are AES-256-GCM encrypted; the client decrypts them using this key.

**Payload wire format** (for client-side decryption):
```
Base64( nonce[12 bytes] || ciphertext || gcm_tag[16 bytes] )
```

**Response `401`:** Missing, non-numeric, or non-positive `X-Original-User-ID` header.

## gRPC API

See [`protos/notification.proto`](protos/notification.proto).

`SendUserPush` — sends an encrypted push notification to all registered devices of a user.

