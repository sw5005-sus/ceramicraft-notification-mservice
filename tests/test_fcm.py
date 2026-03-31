"""Tests for the fcm module (Firebase Cloud Messaging helpers)."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from firebase_admin import messaging

import ceramicraft_notification_mservice.fcm as fcm_module
from ceramicraft_notification_mservice.fcm import initialize_firebase, send_push

pytestmark = pytest.mark.asyncio

_FCM = "ceramicraft_notification_mservice.fcm"


@pytest.fixture(autouse=True)
def reset_firebase():
    """Reset the module-level _firebase_app before each test."""
    original = fcm_module._firebase_app
    fcm_module._firebase_app = None
    yield
    fcm_module._firebase_app = original


# ---------------------------------------------------------------------------
# initialize_firebase
# ---------------------------------------------------------------------------


def test_initialize_firebase_from_json_string():
    """initialize_firebase should accept a JSON string."""
    cred_json = json.dumps(
        {
            "type": "service_account",
            "project_id": "test-project",
            "private_key_id": "key-id",
            "private_key": (
                "-----BEGIN RSA PRIVATE KEY-----\nfake\n-----END RSA PRIVATE KEY-----\n"
            ),
            "client_email": "test@test-project.iam.gserviceaccount.com",
            "client_id": "123",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    )

    mock_cred = MagicMock()
    mock_app = MagicMock()

    with (
        patch(f"{_FCM}.credentials.Certificate", return_value=mock_cred),
        patch(f"{_FCM}.firebase_admin.initialize_app", return_value=mock_app),
    ):
        initialize_firebase(cred_json)

    assert fcm_module._firebase_app is mock_app


def test_initialize_firebase_from_file_path():
    """initialize_firebase should fall back to file path on JSONDecodeError."""
    mock_cred = MagicMock()
    mock_app = MagicMock()

    with (
        patch(f"{_FCM}.credentials.Certificate", return_value=mock_cred),
        patch(f"{_FCM}.firebase_admin.initialize_app", return_value=mock_app),
    ):
        initialize_firebase("/path/to/creds.json")

    assert fcm_module._firebase_app is mock_app


def test_initialize_firebase_empty_string_does_nothing():
    """initialize_firebase with empty string should not init Firebase."""
    initialize_firebase("")
    assert fcm_module._firebase_app is None


def test_initialize_firebase_idempotent():
    """initialize_firebase should not reinitialise if already done."""
    existing_app = MagicMock()
    fcm_module._firebase_app = existing_app

    with patch(f"{_FCM}.firebase_admin.initialize_app") as mock_init:
        initialize_firebase('{"type": "service_account"}')
        mock_init.assert_not_called()

    assert fcm_module._firebase_app is existing_app


def test_initialize_firebase_exception_handled():
    """initialize_firebase should handle unexpected errors gracefully."""
    with patch(
        f"{_FCM}.credentials.Certificate",
        side_effect=Exception("unexpected"),
    ):
        initialize_firebase('{"type": "service_account"}')

    assert fcm_module._firebase_app is None


# ---------------------------------------------------------------------------
# send_push
# ---------------------------------------------------------------------------


async def test_send_push_returns_false_when_not_initialised():
    """send_push should return False when Firebase is not initialised."""
    result = await send_push("token", "enc_body")
    assert result is False


async def test_send_push_success():
    """send_push should return True on successful FCM delivery."""
    fcm_module._firebase_app = MagicMock()

    with patch(
        f"{_FCM}.asyncio.to_thread",
        new=AsyncMock(return_value="message-id"),
    ):
        result = await send_push("fcm_token", "enc123", {"order_id": "42"})

    assert result is True


async def test_send_push_unregistered_token():
    """send_push should return False for unregistered tokens."""
    fcm_module._firebase_app = MagicMock()

    with patch(
        f"{_FCM}.asyncio.to_thread",
        new=AsyncMock(side_effect=messaging.UnregisteredError("unreg")),
    ):
        result = await send_push("bad_token", "enc")

    assert result is False


async def test_send_push_generic_exception():
    """send_push should return False on unexpected errors."""
    fcm_module._firebase_app = MagicMock()

    with patch(
        f"{_FCM}.asyncio.to_thread",
        new=AsyncMock(side_effect=Exception("network error")),
    ):
        result = await send_push("token", "enc")

    assert result is False


async def test_send_push_no_extra_data():
    """send_push with no extra_data should only include encrypted_payload."""
    fcm_module._firebase_app = MagicMock()

    with patch(
        f"{_FCM}.asyncio.to_thread",
        new=AsyncMock(return_value="ok"),
    ) as mock_thread:
        result = await send_push("token", "enc")

    assert result is True
    call_args = mock_thread.call_args
    built_message = call_args.args[1]  # to_thread(messaging.send, message)
    assert built_message.data == {"encrypted_payload": "enc"}
    assert built_message.notification is None
