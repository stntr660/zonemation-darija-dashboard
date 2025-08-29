"""
Encryption utilities for sensitive data
"""
import os
from cryptography.fernet import Fernet
from werkzeug.security import generate_password_hash, check_password_hash


class EncryptionManager:
    """Manages encryption/decryption of sensitive data"""
    
    def __init__(self, key=None):
        """Initialize with encryption key"""
        if key:
            self.cipher = Fernet(key.encode() if isinstance(key, str) else key)
        else:
            # Generate a new key if none provided
            key = Fernet.generate_key()
            self.cipher = Fernet(key)
            print(f"Generated encryption key: {key.decode()}")
            print("Add this to your .env file as ENCRYPTION_KEY")
    
    def encrypt(self, text):
        """Encrypt text data"""
        if not text:
            return None
        if isinstance(text, str):
            text = text.encode()
        return self.cipher.encrypt(text).decode()
    
    def decrypt(self, encrypted_text):
        """Decrypt text data"""
        if not encrypted_text:
            return None
        if isinstance(encrypted_text, str):
            encrypted_text = encrypted_text.encode()
        return self.cipher.decrypt(encrypted_text).decode()


def generate_encryption_key():
    """Generate a new Fernet encryption key"""
    return Fernet.generate_key().decode()


def hash_password(password):
    """Hash a password for storing"""
    return generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)


def verify_password(password_hash, password):
    """Verify a password against its hash"""
    return check_password_hash(password_hash, password)