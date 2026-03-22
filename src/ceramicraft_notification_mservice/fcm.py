import asyncio
import json
import logging
from json import JSONDecodeError
from typing import Optional

import firebase_admin
from firebase_admin import credentials, messaging

logger = logging.getLogger(__name__)

_firebase_app: Optional[firebase_admin.App] = None


def initialize_firebase(cred_env: str) -> None:
    """
    Initializes the Firebase Admin SDK.

    It can be initialized either from a JSON string or a file path
    provided in the `FIREBASE_CREDENTIALS_JSON` environment variable.

    This function is idempotent and will not re-initialize if already done.
    """
    global _firebase_app
    if _firebase_app:
        return

    if not cred_env:
        logger.warning(
            "FIREBASE_CREDENTIALS_JSON is not set. "
            "FCM functionality will be disabled."
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


async def send_push(fcm_token: str, encrypted_payload: str) -> bool:
    """
    Sends an encrypted payload to a device using FCM.

    Args:
        fcm_token: The Firebase Cloud Messaging token for the target device.
        encrypted_payload: The Base64 encoded encrypted payload.

    Returns:
        True if the message was sent successfully, False otherwise.
    """
    if not _firebase_app:
        logger.warning("Firebase not initialized. Cannot send push notification.")
        return False

    message = messaging.Message(
        data={"enc": encrypted_payload},
        token=fcm_token,
        android=messaging.AndroidConfig(priority="high"),
    )

    try:
        # messaging.send is a blocking call, so we run it in a thread
        await asyncio.to_thread(messaging.send, message)
        logger.debug(f"Successfully sent push to token: {fcm_token[:10]}...")
        return True
    except messaging.UnregisteredError:
        logger.info(f"FCM token {fcm_token[:10]}... is unregistered. Marking as failed.")
        return False
    except Exception:
        logger.exception(f"Failed to send push notification to token: {fcm_token[:10]}...")
        return False
