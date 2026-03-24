from pathlib import Path
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, FastAPI, status
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .. import crypto
from ..models.device_token import DeviceToken

_STATIC_DIR = Path(__file__).parent / "static"


class RegisterPushTokenRequest(BaseModel):
    user_id: int
    device_id: str
    fcm_token: str


class RegisterPushTokenResponse(BaseModel):
    aes_key: str  # Base64 encoded


def create_router(
    session_factory: async_sessionmaker[AsyncSession],
) -> APIRouter:
    router = APIRouter(prefix="/notification-ms/v1")

    async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    @router.get("/ping")
    async def ping() -> dict[str, str]:
        return {"status": "ok"}

    @router.post(
        "/push-token",
        status_code=status.HTTP_200_OK,
        response_model=RegisterPushTokenResponse,
    )
    async def register_push_token(
        request: RegisterPushTokenRequest,
        session: AsyncSession = Depends(get_db_session),
    ) -> RegisterPushTokenResponse:
        new_key_bytes = crypto.generate_aes_key()
        new_key_hex = crypto.key_to_hex(new_key_bytes)

        stmt = insert(DeviceToken).values(
            user_id=request.user_id,
            device_id=request.device_id,
            fcm_token=request.fcm_token,
            aes_key=new_key_hex,
        )

        on_conflict_stmt = stmt.on_conflict_do_update(
            index_elements=["user_id", "device_id"],
            set_=dict(
                fcm_token=request.fcm_token,
                aes_key=new_key_hex,
            ),
        )

        await session.execute(on_conflict_stmt)
        await session.commit()

        return RegisterPushTokenResponse(aes_key=crypto.key_to_base64(new_key_bytes))

    return router


def create_app(
    session_factory: async_sessionmaker[AsyncSession],
) -> FastAPI:
    """Creates and returns the FastAPI application."""
    http_app = FastAPI(
        docs_url=None,  # disable default, we serve our own
        redoc_url=None,
        openapi_url="/notification-ms/v1/openapi.json",
    )
    http_app.mount(
        "/notification-ms/v1/static",
        StaticFiles(directory=str(_STATIC_DIR)),
        name="static",
    )
    http_app.include_router(create_router(session_factory))

    @http_app.get(
        "/notification-ms/v1/docs",
        response_class=HTMLResponse,
        include_in_schema=False,
    )
    async def custom_swagger_ui() -> str:
        return """<!DOCTYPE html>
<html><head>
<link rel="stylesheet" href="/notification-ms/v1/static/swagger-ui.css">
</head><body>
<div id="swagger-ui"></div>
<script src="/notification-ms/v1/static/swagger-ui-bundle.js"></script>
<script>SwaggerUIBundle({url:"/notification-ms/v1/openapi.json",dom_id:"#swagger-ui"})</script>
</body></html>"""

    return http_app
