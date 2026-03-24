import asyncio
import logging
import sys

import dotenv
import dttb
import grpc
import typer
import uvicorn
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import ceramicraft_notification_mservice.fcm as fcm_module
from ceramicraft_notification_mservice.config import get_settings
from ceramicraft_notification_mservice.http.router import create_app
from ceramicraft_notification_mservice.models.device_token import Base
from ceramicraft_notification_mservice.pb import notification_pb2_grpc
from ceramicraft_notification_mservice.service import NotificationService

# Apply dttb tracebacks for timestamps on exceptions
dttb.apply()

# Load environment variables
dotenv.load_dotenv()

app = typer.Typer(help="CeramiCraft Notification Microservice CLI")


async def _reset_db() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL)
    typer.echo("Dropping existing tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    typer.echo("Creating tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    typer.secho("Database reset successfully.", fg=typer.colors.GREEN)


async def _start() -> None:
    settings = get_settings()

    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    # Initialise Firebase
    fcm_module.initialize_firebase(settings.FIREBASE_CREDENTIALS_JSON)

    # Build FastAPI app (starts responding to /ping immediately)
    http_app = create_app(session_factory)

    # Build gRPC server
    grpc_server = grpc.aio.server()
    notification_pb2_grpc.add_NotificationServiceServicer_to_server(
        NotificationService(session_factory=session_factory), grpc_server
    )
    grpc_host = settings.NOTIFICATION_MSERVICE_GRPC_HOST
    grpc_address = f"{grpc_host}:{settings.NOTIFICATION_MSERVICE_GRPC_PORT}"
    grpc_server.add_insecure_port(grpc_address)
    await grpc_server.start()
    typer.secho(f"gRPC server listening on {grpc_address}", fg=typer.colors.CYAN)

    # Run HTTP server
    http_host = settings.NOTIFICATION_MSERVICE_HTTP_HOST
    http_address = f"{http_host}:{settings.NOTIFICATION_MSERVICE_HTTP_PORT}"
    typer.secho(f"HTTP server listening on {http_address}", fg=typer.colors.CYAN)
    config = uvicorn.Config(
        http_app,
        host=settings.NOTIFICATION_MSERVICE_HTTP_HOST,
        port=settings.NOTIFICATION_MSERVICE_HTTP_PORT,
        log_level="info",
    )
    server = uvicorn.Server(config)

    async def _init_db() -> None:
        """Initialise DB schema after the HTTP server is already accepting."""
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            typer.secho("Database schema initialised.", fg=typer.colors.GREEN)
        except Exception:
            logging.exception("Failed to initialise database schema")

    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(server.serve())
            tg.create_task(grpc_server.wait_for_termination())
            tg.create_task(_init_db())
    finally:
        await grpc_server.stop(grace=5)


@app.command()
def reset_db() -> None:
    """Reset the database schema (drop all tables and recreate)."""
    asyncio.run(_reset_db())


@app.command()
def start() -> None:
    """Start the HTTP and gRPC servers."""
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(_start())


if __name__ == "__main__":
    app()
