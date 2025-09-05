from cryptography.fernet import Fernet
import os

KEY_PATH = 'config/secret.key'

def generate_key():
    """
    Generates a new encryption key and saves it to the key file.
    """
    key = Fernet.generate_key()
    with open(KEY_PATH, 'wb') as key_file:
        key_file.write(key)
    return key

def load_key():
    """
    Loads the encryption key from the key file.
    If the key file does not exist, it generates a new one.
    """
    if not os.path.exists(KEY_PATH):
        return generate_key()
    with open(KEY_PATH, 'rb') as key_file:
        return key_file.read()

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
