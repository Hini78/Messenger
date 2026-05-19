import logging
import os
import hashlib
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

# Configure logging to show the "inner workings" of the encryption process
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("CryptoEngine")


class CryptoEngine:
    """
    Implements the hybrid encryption scheme:
    1. AES-256 for message content (Symmetric)
    2. RSA-2048 for session key exchange (Asymmetric)
    3. SHA-256 for integrity checks (Hashing)
    """

    @staticmethod
    def generate_rsa_keypair():
        logger.info("Generating RSA-2048 keypair...")
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        public_key = private_key.public_key()

        priv_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        pub_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        logger.info("RSA Keypair generated successfully.")
        return priv_pem, pub_pem

    @staticmethod
    def encrypt_data(data: bytes, recipient_public_key_pem: bytes, sender_public_key_pem: bytes = None):
        logger.info("--- STARTING ENCRYPTION PROCESS ---")

        # 1. Generate a random AES session key (256 bits)
        session_key = os.urandom(32)
        iv = os.urandom(16)
        logger.info(f"Generated random 256-bit AES session key: {session_key.hex()[:10]}...")
        logger.info(f"Generated IV: {iv.hex()}")

        # 2. Encrypt data with AES
        logger.info("Encrypting data with AES-256-CFB...")
        cipher = Cipher(algorithms.AES(session_key), modes.CFB(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        encrypted_content = encryptor.update(data) + encryptor.finalize()
        logger.info(f"Data encrypted. Length: {len(encrypted_content)} bytes")

        # 3. Encrypt the session key with Recipient's RSA Public Key (Key Wrapping)
        logger.info("Wrapping AES session key with Recipient's RSA Public Key...")
        recipient_pub_key = serialization.load_pem_public_key(recipient_public_key_pem, backend=default_backend())
        encrypted_session_key = recipient_pub_key.encrypt(
            session_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

        encrypted_session_key_sender = None
        if sender_public_key_pem:
            logger.info("Wrapping AES session key with Sender's RSA Public Key...")
            sender_pub_key = serialization.load_pem_public_key(sender_public_key_pem, backend=default_backend())
            encrypted_session_key_sender = sender_pub_key.encrypt(
                session_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )

        logger.info("Session key wrapped successfully.")

        # 4. Create Integrity Hash (SHA-256)
        logger.info("Generating SHA-256 integrity hash...")
        hasher = hashlib.sha256()
        hasher.update(data)
        integrity_hash = hasher.hexdigest()
        logger.info(f"Integrity Hash: {integrity_hash}")

        return {
            "encrypted_content": encrypted_content.hex(),
            "encrypted_session_key": encrypted_session_key.hex(),
            "encrypted_session_key_sender": encrypted_session_key_sender.hex() if encrypted_session_key_sender else None,
            "iv": iv.hex(),
            "integrity_hash": integrity_hash
        }

    # Backward compatibility
    @staticmethod
    def encrypt_message(message_text: str, recipient_public_key_pem: bytes, sender_public_key_pem: bytes = None):
        return CryptoEngine.encrypt_data(message_text.encode(), recipient_public_key_pem, sender_public_key_pem)

    @staticmethod
    def decrypt_data(encrypted_package: dict, recipient_private_key_pem: bytes):
        logger.info("--- STARTING DECRYPTION PROCESS ---")

        # 1. Unwrap the AES session key using Private RSA Key
        logger.info("Unwrapping AES session key with Recipient's RSA Private Key...")
        private_key = serialization.load_pem_private_key(recipient_private_key_pem, password=None,
                                                         backend=default_backend())
        encrypted_session_key = bytes.fromhex(encrypted_package["encrypted_session_key"])

        session_key = private_key.decrypt(
            encrypted_session_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        logger.info("Session key unwrapped successfully.")

        # 2. Decrypt content with the unwrapped session key
        logger.info("Decrypting data with AES-256-CFB...")
        iv = bytes.fromhex(encrypted_package["iv"])
        encrypted_content = bytes.fromhex(encrypted_package["encrypted_content"])

        cipher = Cipher(algorithms.AES(session_key), modes.CFB(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        decrypted_data = decryptor.update(encrypted_content) + decryptor.finalize()
        logger.info(f"Decryption complete. Data size: {len(decrypted_data)} bytes")

        # 3. Verify Integrity
        logger.info("Verifying SHA-256 integrity hash...")
        hasher = hashlib.sha256()
        hasher.update(decrypted_data)
        current_hash = hasher.hexdigest()

        if current_hash == encrypted_package["integrity_hash"]:
            logger.info("INTEGRITY VERIFIED: Hashes match.")
            return decrypted_data, True
        else:
            logger.error("INTEGRITY FAILED: Hashes do not match!")
            return decrypted_data, False

    # Backward compatibility
    @staticmethod
    def decrypt_message(encrypted_package: dict, recipient_private_key_pem: bytes):
        data, ok = CryptoEngine.decrypt_data(encrypted_package, recipient_private_key_pem)
        try:
            return data.decode(), ok
        except:
            return "[Error: Data is binary, use decrypt_data instead]", ok
