import pytest
import os
from .crypto_engine import CryptoEngine

def test_rsa_key_generation():
    priv, pub = CryptoEngine.generate_rsa_keypair()
    assert priv.startswith(b"-----BEGIN PRIVATE KEY-----")
    assert pub.startswith(b"-----BEGIN PUBLIC KEY-----")

def test_full_encryption_decryption_cycle():
    # Setup keys
    priv, pub = CryptoEngine.generate_rsa_keypair()
    original_message = "Secret corporate data 12345"
    
    # Encrypt
    package = CryptoEngine.encrypt_message(original_message, pub)
    assert "encrypted_content" in package
    assert "encrypted_session_key" in package
    assert "iv" in package
    assert "integrity_hash" in package
    
    # Decrypt
    decrypted_message, integrity = CryptoEngine.decrypt_message(package, priv)
    
    assert integrity is True
    assert decrypted_message == original_message

def test_integrity_failure():
    # Setup keys
    priv, pub = CryptoEngine.generate_rsa_keypair()
    original_message = "Safe content"
    
    # Encrypt
    package = CryptoEngine.encrypt_message(original_message, pub)
    
    # Manually tamper with the encrypted content
    tampered_content = list(bytes.fromhex(package["encrypted_content"]))
    tampered_content[0] = (tampered_content[0] + 1) % 256
    package["encrypted_content"] = bytes(tampered_content).hex()
    
    # Decrypt
    decrypted_message, integrity = CryptoEngine.decrypt_message(package, priv)
    
    # The message text might be garbled, but integrity must fail
    assert integrity is False

if __name__ == "__main__":
    pytest.main([__file__])
