import asyncio
import logging

import grpc
import typer
import uvicorn
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from ceramicraft_notification_mservice.config import get_settings
from ceramicraft_notification_mservice.fcm import initialize_firebase
from ceramicraft_notification_mservice.http.router import create_app
from ceramicraft_notification_mservice.models.device_token import Base
from ceramicraft_notification_mservice.pb import notification_pb2_grpc
from ceramicraft_notification_mservice.service import NotificationService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = typer.Typer()
settings = get_settings()


async def _start_all(
    http_app: FastAPI,
    grpc_server: grpc.aio.Server,
    http_host: str,
    http_port: int,
) -> None:
    """Starts both the HTTP and gRPC servers."""
    uvicorn_config = uvicorn.Config(
        http_app, host=http_host, port=http_port, log_level="info"
    )
    uvicorn_server = uvicorn.Server(uvicorn_config)

    logger.info(
        "Starting gRPC server on "
        f"{settings.NOTIFICATION_GRPC_HOST}:{settings.NOTIFICATION_GRPC_PORT}"
    )
    await grpc_server.start()

    logger.info(f"Starting HTTP server on {http_host}:{http_port}")
    await asyncio.gather(uvicorn_server.serve(), grpc_server.wait_for_termination())


@app.command()
def start(
    http_host: str = typer.Option(
        settings.NOTIFICATION_HTTP_HOST,
        "--http-host",
        "-h",
        help="HTTP server host",
    ),
    http_port: int = typer.Option(
        settings.NOTIFICATION_HTTP_PORT,
        "--http-port",
        "-p",
        help="HTTP server port",
    ),
) -> None:
    """Starts the notification microservice (HTTP and gRPC servers)."""
    import os

    cred = os.getenv("FIREBASE_CREDENTIALS_JSON", "")
    if cred:
        initialize_firebase(cred)
    else:
        logger.warning("FIREBASE_CREDENTIALS_JSON not set - FCM push will not work")

    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def init_db() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(init_db())

    grpc_server = grpc.aio.server()
    service_impl = NotificationService(session_factory)
    notification_pb2_grpc.add_NotificationServiceServicer_to_server(
        service_impl, grpc_server
    )
    grpc_server.add_insecure_port(
        f"{settings.NOTIFICATION_GRPC_HOST}:{settings.NOTIFICATION_GRPC_PORT}"
    )

    http_app = create_app(session_factory)

    try:
        asyncio.run(_start_all(http_app, grpc_server, http_host, http_port))
    except (KeyboardInterrupt, SystemExit):
        logger.info("Servers shutting down.")


@app.command()
def reset_db() -> None:
    """Drops and recreates all database tables."""

    async def _reset() -> None:
        engine = create_async_engine(settings.DATABASE_URL)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()
        print("Database has been reset.")

    asyncio.run(_reset())


if __name__ == "__main__":
    app()
