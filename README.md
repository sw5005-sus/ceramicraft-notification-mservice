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
