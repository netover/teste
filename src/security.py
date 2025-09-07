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

def decrypt_password(encrypted_password: bytes, key: bytes) -> str:
    """
    Decrypts an encrypted password using the provided key.
    """
    f = Fernet(key)
    decrypted_password = f.decrypt(encrypted_password).decode()
    return decrypted_password
