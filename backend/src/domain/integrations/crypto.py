import base64
import hashlib
import hmac
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from backend.src.core.config import settings
from backend.src.core.errors import ValidationException


def _get_encryption_key(key_str: str | None = None) -> bytes:
    """Normalize and validate the 32-byte (256-bit) encryption key."""
    raw_key = key_str or settings.ENCRYPTION_KEY
    try:
        decoded = base64.b64decode(raw_key)
        if len(decoded) == 32:
            return decoded
    except Exception:
        pass

    key_bytes = raw_key.encode("utf-8")
    if len(key_bytes) == 32:
        return key_bytes

    # If key is shorter or longer, derive 32-byte key using SHA-256
    return hashlib.sha256(key_bytes).digest()


def encrypt_credential(plaintext: str, key: str | None = None) -> str:
    """Encrypt a sensitive plaintext string using AES-256-GCM.

    Returns:
        Base64-encoded string containing [12-byte nonce + ciphertext + 16-byte auth tag].
    """
    if not plaintext:
        return ""
    key_bytes = _get_encryption_key(key)
    aesgcm = AESGCM(key_bytes)
    nonce = os.urandom(12)  # 96-bit nonce recommended for GCM
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + ciphertext).decode("utf-8")


def decrypt_credential(ciphertext_b64: str, key: str | None = None) -> str:
    """Decrypt an AES-256-GCM encrypted ciphertext base64 string.

    Raises:
        ValidationException: If decryption or authentication verification fails.
    """
    if not ciphertext_b64:
        return ""
    try:
        raw_data = base64.b64decode(ciphertext_b64.encode("utf-8"))
        if len(raw_data) < 28:  # 12 nonce + at least 16 tag
            raise ValueError("Encrypted data payload is too short.")

        nonce = raw_data[:12]
        ciphertext = raw_data[12:]
        key_bytes = _get_encryption_key(key)
        aesgcm = AESGCM(key_bytes)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode("utf-8")
    except (InvalidTag, ValueError, Exception) as exc:
        raise ValidationException(
            "Failed to decrypt stored credential. Key mismatch or corrupted data.",
            details=[{"field": "api_key_encrypted", "issue": "Decryption failed"}],
        ) from exc


def verify_shopify_hmac(raw_body: bytes, hmac_header: str | None, secret: str) -> bool:
    """Validate Shopify webhook authenticity using HMAC-SHA256 signature verification.

    Compares the calculated HMAC against the 'X-Shopify-Hmac-Sha256' header
    using constant-time comparison to prevent timing attacks.
    """
    if not hmac_header or not secret:
        return False

    calculated_hmac = base64.b64encode(
        hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).digest()
    ).decode("utf-8")

    return hmac.compare_digest(calculated_hmac, hmac_header.strip())
