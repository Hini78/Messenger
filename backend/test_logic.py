from .crypto_engine import CryptoEngine
import logging


# Setup simple testing flow
def run_demonstration():
    print("--- CORPORATE ENCRYPTED MESSAGE EXCHANGE DEMO ---")

    # 1. User B (Recipient) generates keys
    print("[User B] Generating RSA keys for secure communication...")
    priv_b, pub_b = CryptoEngine.generate_rsa_keypair()

    # 2. User A (Sender) wants to send message to User B
    message_text = "Highly confidential project data: Project Antigravity is GO."
    print(f"[User A] Preparing to send message: '{message_text}'")

    # User A encrypts using User B's public key
    print("[User A] Encrypting message using User B's Public Key...")
    encrypted_pkg = CryptoEngine.encrypt_message(message_text, pub_b)

    print("\n[NETWORK] Package transmitted over corporate LAN:")
    for k, v in encrypted_pkg.items():
        print(f"  {k}: {v[:50]}...")

    print("\n[User B] Received encrypted package. Attempting decryption...")

    # 3. User B decrypts using their private key
    decrypted_text, integrity = CryptoEngine.decrypt_message(encrypted_pkg, priv_b)

    if integrity:
        print(f"[User B] Success! Decrypted message: '{decrypted_text}'")
        print("[User B] Integrity check passed (SHA-256 matches).")
    else:
        print("[User B] ERROR: Integrity check failed. Message may have been tampered with.")


if __name__ == "__main__":
    run_demonstration()
