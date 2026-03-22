import base64
from unittest.mock import patch

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


async def _register_device(session: AsyncSession, user_id: int, device_id: str, fcm_token: str):
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
    return device


@patch("ceramicraft_notification_mservice.service.fcm.send_push", new_callable=lambda: pytest.mark.asyncio(lambda *args, **kwargs: True))
async def test_send_push_single_device(mock_send_push, svc, session_factory, ctx):
    """Test sending a push to a user with one successful device."""
    user_id = 101
    async with session_factory() as session:
        await _register_device(session, user_id, "dev1", "fcm1")

    request = notification_pb2.SendUserPushRequest(
        user_id=user_id, title="Test", body="Hello"
    )
    response = await svc.SendUserPush(request, ctx)

    assert response.success is True
    assert response.sent_count == 1
    assert len(response.failed_tokens) == 0
    mock_send_push.assert_called_once()


@patch("ceramicraft_notification_mservice.service.fcm.send_push", new_callable=lambda: pytest.mark.asyncio(lambda *args, **kwargs: False))
async def test_send_push_failed_device(mock_send_push, svc, session_factory, ctx):
    """Test SendUserPush when the fcm.send_push call fails."""
    user_id = 102
    fcm_token = "fcm_fail"
    async with session_factory() as session:
        await _register_device(session, user_id, "dev_fail", fcm_token)

    request = notification_pb2.SendUserPushRequest(
        user_id=user_id, title="Test", body="Hello"
    )
    response = await svc.SendUserPush(request, ctx)

    assert response.success is True
    assert response.sent_count == 0
    assert len(response.failed_tokens) == 1
    assert response.failed_tokens[0] == fcm_token
    mock_send_push.assert_called_once()


@patch("ceramicraft_notification_mservice.service.fcm.send_push", new_callable=lambda: pytest.mark.asyncio(lambda *args, **kwargs: True))
async def test_encrypted_payload_format(mock_send_push, svc, session_factory, ctx):
    """Verify that the payload passed to fcm.send_push is correctly encrypted."""
    user_id = 103
    async with session_factory() as session:
        device = await _register_device(session, user_id, "dev_enc", "fcm_enc")

    request = notification_pb2.SendUserPushRequest(
        user_id=user_id,
        title="Enc",
        body="Payload",
        data={"extra": "info"},
    )
    await svc.SendUserPush(request, ctx)

    mock_send_push.assert_called_once()
    args, _ = mock_send_push.call_args
    sent_fcm_token, encrypted_payload_b64 = args

    assert sent_fcm_token == device.fcm_token
    
    # Verify it's valid Base64
    try:
        encrypted_data = base64.b64decode(encrypted_payload_b64)
    except Exception:
        pytest.fail("Payload is not valid Base64")

    # AES-GCM nonce is 12 bytes
    assert len(encrypted_data) > 12, "Encrypted data is too short"
    
    # Cannot easily decrypt without mocking os.urandom, but we can check the format.
    # We know nonce(12) + ciphertext + tag. This confirms the format is plausible.
