import base64
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from ceramicraft_notification_mservice.crypto import generate_aes_key, key_to_hex
from ceramicraft_notification_mservice.models.device_token import DeviceToken
from ceramicraft_notification_mservice.pb import notification_pb2

pytestmark = pytest.mark.asyncio


async def test_send_push_no_devices(svc, ctx):
    """Test SendUserPush when the user has no registered devices."""
    request = notification_pb2.SendUserPushRequest(user_id=999)
    response = await svc.SendUserPush(request, ctx)

    assert response.success is True
    assert response.sent_count == 0
    assert len(response.failed_tokens) == 0


async def _register_device(
    session: AsyncSession, user_id: int, device_id: str, fcm_token: str
) -> DeviceToken:
    """Helper to directly insert a device into the DB."""
    key_bytes = generate_aes_key()
    key_hex = key_to_hex(key_bytes)
    device = DeviceToken(
        user_id=user_id,
        device_id=device_id,
        fcm_token=fcm_token,
        aes_key=key_hex,
    )
    session.add(device)
    await session.commit()
    await session.refresh(device)
    return device


async def test_send_push_single_device(svc, session_factory, ctx):
    """Test sending a push to a user with one successful device."""
    user_id = 101
    async with session_factory() as session:
        await _register_device(session, user_id, "dev1", "fcm1")

    request = notification_pb2.SendUserPushRequest(
        user_id=user_id, title="Test", body="Hello"
    )
    with patch(
        "ceramicraft_notification_mservice.service.fcm.send_push",
        new=AsyncMock(return_value=True),
    ):
        response = await svc.SendUserPush(request, ctx)

    assert response.success is True
    assert response.sent_count == 1
    assert len(response.failed_tokens) == 0


async def test_send_push_failed_device(svc, session_factory, ctx):
    """Test SendUserPush when the fcm.send_push call fails."""
    user_id = 102
    fcm_token = "fcm_fail"
    async with session_factory() as session:
        await _register_device(session, user_id, "dev_fail", fcm_token)

    request = notification_pb2.SendUserPushRequest(
        user_id=user_id, title="Test", body="Hello"
    )
    with patch(
        "ceramicraft_notification_mservice.service.fcm.send_push",
        new=AsyncMock(return_value=False),
    ):
        response = await svc.SendUserPush(request, ctx)

    assert response.success is True
    assert response.sent_count == 0
    assert len(response.failed_tokens) == 1
    assert response.failed_tokens[0] == fcm_token


async def test_encrypted_payload_format(svc, session_factory, ctx):
    """Verify fcm.send_push receives correct title, encrypted body and extra_data."""
    user_id = 103
    async with session_factory() as session:
        device = await _register_device(session, user_id, "dev_enc", "fcm_enc")

    request = notification_pb2.SendUserPushRequest(
        user_id=user_id,
        title="Enc",
        body="Payload",
        data={"extra": "info"},
    )
    mock_send = AsyncMock(return_value=True)
    with patch(
        "ceramicraft_notification_mservice.service.fcm.send_push",
        new=mock_send,
    ):
        await svc.SendUserPush(request, ctx)

    mock_send.assert_called_once()
    kwargs = mock_send.call_args.kwargs

    assert kwargs["fcm_token"] == device.fcm_token
    assert kwargs["title"] == "Enc"
    assert kwargs["extra_data"] == {"extra": "info"}

    encrypted_payload_b64 = kwargs["encrypted_body"]

    # Verify it's valid Base64
    try:
        encrypted_data = base64.b64decode(encrypted_payload_b64)
    except Exception:
        pytest.fail("Payload is not valid Base64")

    # AES-GCM: nonce(12 bytes) + ciphertext + tag(16 bytes), minimum > 12
    assert len(encrypted_data) > 12, "Encrypted data is too short"


async def test_send_push_multiple_devices(svc, session_factory, ctx):
    """Test that push is sent to all devices of a user independently."""
    user_id = 104
    async with session_factory() as session:
        await _register_device(session, user_id, "devA", "fcmA")
        await _register_device(session, user_id, "devB", "fcmB")

    request = notification_pb2.SendUserPushRequest(
        user_id=user_id, title="Multi", body="Hello all"
    )
    mock_send = AsyncMock(return_value=True)
    with patch(
        "ceramicraft_notification_mservice.service.fcm.send_push",
        new=mock_send,
    ):
        response = await svc.SendUserPush(request, ctx)

    assert response.success is True
    assert response.sent_count == 2
    assert mock_send.call_count == 2

    # Each device has its own AES key, so ciphertexts differ
    call1_body = mock_send.call_args_list[0].kwargs["encrypted_body"]
    call2_body = mock_send.call_args_list[1].kwargs["encrypted_body"]
    assert call1_body != call2_body


async def test_send_push_no_extra_data(svc, session_factory, ctx):
    """Test that extra_data is None when request.data is empty."""
    user_id = 105
    async with session_factory() as session:
        await _register_device(session, user_id, "dev_nodata", "fcm_nodata")

    request = notification_pb2.SendUserPushRequest(
        user_id=user_id, title="NoData", body="Body"
    )
    mock_send = AsyncMock(return_value=True)
    with patch(
        "ceramicraft_notification_mservice.service.fcm.send_push",
        new=mock_send,
    ):
        await svc.SendUserPush(request, ctx)

    kwargs = mock_send.call_args.kwargs
    assert kwargs["extra_data"] is None
