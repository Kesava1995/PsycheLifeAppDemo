"""
Reversible encryption for sensitive values (e.g. SMTP app password).
Uses Fernet (symmetric) so we can decrypt when sending email.
"""
import base64
import hashlib

from cryptography.fernet import Fernet
from cryptography.fernet import InvalidToken


def _get_key():
    """Get Fernet key from Flask config. Derive from SECRET_KEY if SMTP_ENCRYPTION_KEY not set."""
    from flask import current_app
    key = current_app.config.get('SMTP_ENCRYPTION_KEY')
    if key:
        if isinstance(key, str):
            key = key.encode('utf-8')
        return key
    secret = current_app.config.get('SECRET_KEY', 'default-secret-change-me')
    if isinstance(secret, str):
        secret = secret.encode('utf-8')
    raw = hashlib.sha256(secret).digest()
    return base64.urlsafe_b64encode(raw)


def encrypt_smtp_password(plain_text):
    """Encrypt a plain-text password for storage. Returns str (url-safe base64)."""
    if not plain_text:
        return None
    key = _get_key()
    f = Fernet(key)
    token = f.encrypt(plain_text.encode('utf-8'))
    return token.decode('ascii')


def decrypt_smtp_password(cipher_text):
    """
    Decrypt stored password. Returns plain str, or None if invalid/empty.
    If decryption fails (e.g. legacy plain text), returns cipher_text as-is for backward compatibility.
    """
    if not cipher_text:
        return None
    try:
        key = _get_key()
        f = Fernet(key)
        return f.decrypt(cipher_text.encode('ascii')).decode('utf-8')
    except (InvalidToken, Exception):
        return cipher_text
