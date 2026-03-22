import asyncio
import json
import logging
from json import JSONDecodeError
from typing import Optional

import firebase_admin
from firebase_admin import credentials, messaging

logger = logging.getLogger(__name__)

_firebase_app: Optional[firebase_admin.App] = None

# Generic placeholder shown in system tray — never put real content here
_NOTIFICATION_BODY_PLACEHOLDER = "You have a new secure message. Tap to view details."


def initialize_firebase(cred_env: str) -> None:
    """
    Initializes the Firebase Admin SDK.

    It can be initialized either from a JSON string or a file path
    provided in the `FIREBASE_CREDENTIALS_JSON` environment variable.

    This function is idempotent and will not re-initialized if already done.
    """
    global _firebase_app
    if _firebase_app:
        return

    if not cred_env:
        logger.warning(
            "FIREBASE_CREDENTIALS_JSON is not set. FCM functionality will be disabled."
        )
        return

    try:
        # First, try to load as a JSON string
        cred_dict = json.loads(cred_env)
        cred = credentials.Certificate(cred_dict)
    except JSONDecodeError:
        # If that fails, treat it as a file path
        logger.info("Parsing FIREBASE_CREDENTIALS_JSON as a file path.")
        cred = credentials.Certificate(cred_env)
    except Exception as e:
        logger.error(f"Failed to initialize Firebase credentials: {e}")
        return

    _firebase_app = firebase_admin.initialize_app(cred)
    logger.info("Firebase Admin SDK initialized successfully.")


async def send_push(
    fcm_token: str,
    title: str,
    encrypted_body: str,
    extra_data: dict[str, str] | None = None,
) -> bool:
    """
    Sends a push notification to a device using FCM.

    The notification block carries a plaintext title and a generic body
    placeholder (so the OS can display a tray notification without exposing
    sensitive content). The real body ciphertext is delivered in the data
    block under the key ``encrypted_payload``, alongside any caller-supplied
    extra fields.

    Args:
        fcm_token: The Firebase Cloud Messaging registration token.
        title: Plaintext notification title shown in the system tray.
        encrypted_body: Base64-encoded AES-GCM ciphertext of the message body.
        extra_data: Optional extra key/value pairs forwarded to the app
                    (e.g. ``action_type``, ``order_id``).

    Returns:
        True if the message was sent successfully, False otherwise.
    """
    if not _firebase_app:
        logger.warning("Firebase not initialized. Cannot send push notification.")
        return False

    data: dict[str, str] = {"encrypted_payload": encrypted_body}
    if extra_data:
        data.update(extra_data)

    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=_NOTIFICATION_BODY_PLACEHOLDER,
        ),
        data=data,
        token=fcm_token,
        android=messaging.AndroidConfig(priority="high"),
    )

    try:
        await asyncio.to_thread(messaging.send, message)
        logger.debug(f"Successfully sent push to token: {fcm_token[:10]}...")
        return True
    except messaging.UnregisteredError:
        logger.info(
            f"FCM token {fcm_token[:10]}... is unregistered. Marking as failed."
        )
        return False
    except Exception:
        logger.exception(
            f"Failed to send push notification to token: {fcm_token[:10]}..."
        )
        return False
