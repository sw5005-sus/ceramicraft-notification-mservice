import base64
import logging
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)


def generate_aes_key() -> bytes:
    """Generates a random 32-byte (256-bit) AES key."""
    return os.urandom(32)


def key_to_hex(
    key: bytes,
) -> str:
    """Converts a bytes key to its hexadecimal string representation."""
    return key.hex()


def hex_to_key(
    hex_str: str,
) -> bytes:
    """Converts a hexadecimal string back to a bytes key."""
    return bytes.fromhex(hex_str)


def key_to_base64(
    key: bytes,
) -> str:
    """Encodes a bytes key into a Base64 string for API responses."""
    return base64.b64encode(key).decode("utf-8")


def encrypt_payload(
    key_hex: str,
    payload: str,
) -> str:
    """
    Encrypts a payload using AES-256-GCM.

    Args:
        key_hex: The 64-character hex-encoded AES key.
        payload: The plaintext string to encrypt.

    Returns:
        A Base64 encoded string containing the nonce + ciphertext + tag.
    """
    key = hex_to_key(key_hex)
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # GCM standard nonce size
    payload_bytes = payload.encode("utf-8")
    ciphertext_with_tag = aesgcm.encrypt(nonce, payload_bytes, None)
    logger.debug(
        "AES-256-GCM encrypt | plaintext_len=%d | ciphertext_len=%d",
        len(payload_bytes),
        len(ciphertext_with_tag),
    )
    # Prepend the nonce to the ciphertext for decryption
    encrypted_data = nonce + ciphertext_with_tag
    return base64.b64encode(encrypted_data).decode("utf-8")
