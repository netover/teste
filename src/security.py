from cryptography.fernet import Fernet
from pathlib import Path

KEY_PATH = Path('config/secret.key')

def generate_key() -> bytes:
    """
    Generates a new encryption key and saves it to the key file.
    """
    key = Fernet.generate_key()
    # Ensure the config directory exists
    KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
    KEY_PATH.write_bytes(key)
    return key

def load_key() -> bytes:
    """
    Loads the encryption key from the key file.
    If the key file does not exist, it generates a new one.
    """
    if not KEY_PATH.exists():
        return generate_key()
    return KEY_PATH.read_bytes()

def encrypt_password(password: str, key: bytes) -> bytes:
    """
    Encrypts a password using the provided key.
    """
    f = Fernet(key)
    encrypted_password = f.encrypt(password.encode())
    return encrypted_password

from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

from src.core import config

api_key_header = APIKeyHeader(name="X-API-Key")

def get_api_key(api_key: str = Security(api_key_header)):
    """
    FastAPI dependency to verify the X-API-Key header.
    """
    if not config.API_KEY:
        # If no API_KEY is configured, security is disabled.
        # This is useful for local development but should be logged as a warning.
        import logging
        logging.warning("API_KEY is not set in config. Security for protected endpoints is disabled.")
        return

    if api_key == config.API_KEY:
        return api_key
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key",
        )

def decrypt_password(encrypted_password: bytes, key: bytes) -> str:
    """
    Decrypts an encrypted password using the provided key.
    """
    f = Fernet(key)
    decrypted_password = f.decrypt(encrypted_password).decode()
    return decrypted_password
