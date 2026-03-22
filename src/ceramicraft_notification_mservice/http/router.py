from typing import AsyncGenerator

from fastapi import APIRouter, Depends, FastAPI, status
from pydantic import BaseModel
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .. import crypto
from ..models.device_token import DeviceToken


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
    http_app = FastAPI()
    http_app.include_router(create_router(session_factory))
    return http_app
