import base64
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ceramicraft_notification_mservice.models.device_token import DeviceToken

pytestmark = pytest.mark.asyncio

# Header injected by the API Gateway (mirrors Go service behaviour)
_AUTH_HEADERS = {"X-Original-User-ID": "123"}


async def test_ping(http_client):
    """Test the ping endpoint."""
    response = await http_client.get("/notification-ms/v1/ping")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_register_new_device(http_client, session_factory):
    """Test registering a new device token."""
    user_id = 123
    device_id = str(uuid.uuid4())
    fcm_token = "test_fcm_token"

    response = await http_client.post(
        "/notification-ms/v1/push-token",
        json={"device_id": device_id, "fcm_token": fcm_token},
        headers={"X-Original-User-ID": str(user_id)},
    )

    assert response.status_code == 200
    data = response.json()
    assert "aes_key" in data

    # Verify the key is valid Base64 and decodes to 32 bytes
    key_bytes = base64.b64decode(data["aes_key"])
    assert len(key_bytes) == 32

    # Verify the device was actually saved in the DB
    async with session_factory() as session:
        stmt = select(DeviceToken).where(
            DeviceToken.user_id == user_id, DeviceToken.device_id == device_id
        )
        result = await session.execute(stmt)
        device = result.scalar_one_or_none()
        assert device is not None
        assert device.fcm_token == fcm_token


async def test_register_same_device_gets_new_key(http_client, session_factory):
    """Test that reregistering the same device issues a new AES key."""
    user_id = 456
    device_id = str(uuid.uuid4())
    headers = {"X-Original-User-ID": str(user_id)}

    # First registration
    response1 = await http_client.post(
        "/notification-ms/v1/push-token",
        json={"device_id": device_id, "fcm_token": "token1"},
        headers=headers,
    )
    assert response1.status_code == 200
    key1 = response1.json()["aes_key"]

    # Second registration with a new FCM token
    response2 = await http_client.post(
        "/notification-ms/v1/push-token",
        json={"device_id": device_id, "fcm_token": "token2"},
        headers=headers,
    )
    assert response2.status_code == 200
    key2 = response2.json()["aes_key"]

    assert key1 != key2

    # Verify the token was updated in the DB
    async with session_factory() as session:
        stmt = select(DeviceToken).where(DeviceToken.device_id == device_id)
        result = await session.execute(stmt)
        device = result.scalar_one()
        assert device.fcm_token == "token2"


async def test_register_different_devices_same_user(
    http_client, session_factory: async_sessionmaker[AsyncSession]
):
    """Test that two different devices for the same user are stored correctly."""
    user_id = 789
    device_id1 = str(uuid.uuid4())
    device_id2 = str(uuid.uuid4())
    headers = {"X-Original-User-ID": str(user_id)}

    await http_client.post(
        "/notification-ms/v1/push-token",
        json={"device_id": device_id1, "fcm_token": "token_dev1"},
        headers=headers,
    )
    await http_client.post(
        "/notification-ms/v1/push-token",
        json={"device_id": device_id2, "fcm_token": "token_dev2"},
        headers=headers,
    )

    # Verify both devices exist for the user
    async with session_factory() as session:
        stmt = select(DeviceToken).where(DeviceToken.user_id == user_id)
        result = await session.execute(stmt)
        devices = result.scalars().all()
        assert len(devices) == 2
        assert {d.device_id for d in devices} == {device_id1, device_id2}


async def test_register_missing_header_returns_401(http_client):
    """Test that missing X-Original-User-ID header returns 401."""
    response = await http_client.post(
        "/notification-ms/v1/push-token",
        json={"device_id": "some-device", "fcm_token": "some-token"},
    )
    assert response.status_code == 401


async def test_register_invalid_header_returns_401(http_client):
    """Test that non-numeric X-Original-User-ID returns 401."""
    response = await http_client.post(
        "/notification-ms/v1/push-token",
        json={"device_id": "some-device", "fcm_token": "some-token"},
        headers={"X-Original-User-ID": "not-a-number"},
    )
    assert response.status_code == 401


async def test_register_zero_user_id_returns_401(http_client):
    """Test that user ID <= 0 returns 401."""
    response = await http_client.post(
        "/notification-ms/v1/push-token",
        json={"device_id": "some-device", "fcm_token": "some-token"},
        headers={"X-Original-User-ID": "0"},
    )
    assert response.status_code == 401
