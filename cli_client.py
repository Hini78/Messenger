import requests
import sys
import os
import json
from backend.crypto_engine import CryptoEngine

# URL вашего запущенного сервера FastAPI
BASE_URL = "http://127.0.0.1:8000"
KEYS_DIR = "keys"


class SecureClient:
    def __init__(self):
        self.username = None
        self.user_id = None
        self.private_key = None
        self.public_key = None

        if not os.path.exists(KEYS_DIR):
            os.makedirs(KEYS_DIR)

    def _save_keys(self):
        """Сохраняет ключи пользователя в локальную папку."""
        priv_path = os.path.join(KEYS_DIR, f"{self.username}_private.pem")
        pub_path = os.path.join(KEYS_DIR, f"{self.username}_public.pem")

        with open(priv_path, "wb") as f:
            f.write(self.private_key)
        with open(pub_path, "wb") as f:
            f.write(self.public_key)

    def _load_keys(self):
        """Загружает ключи из локальной папки."""
        priv_path = os.path.join(KEYS_DIR, f"{self.username}_private.pem")
        pub_path = os.path.join(KEYS_DIR, f"{self.username}_public.pem")

        if os.path.exists(priv_path) and os.path.exists(pub_path):
            with open(priv_path, "rb") as f:
                self.private_key = f.read()
            with open(pub_path, "rb") as f:
                self.public_key = f.read()
            return True
        return False

    def register(self):
        print("\n--- Регистрация ---")
        username = input("Придумайте логин: ")
        password = input("Придумайте пароль: ")

        # Генерация ключей на стороне клиента
        priv, pub = CryptoEngine.generate_rsa_keypair()

        payload = {
            "username": username,
            "password": password,
            "public_key": pub.decode('utf-8')
        }

        try:
            response = requests.post(f"{BASE_URL}/register", json=payload, timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.user_id = data["id"]
                self.username = username
                self.private_key = priv
                self.public_key = pub
                self._save_keys()
                print(f"[Успех] Вы зарегистрированы! Ваш ID: {self.user_id}")
                print(f"[Инфо] Приватный ключ сохранен в {KEYS_DIR}/")
            else:
                print(f"[Ошибка сервера {response.status_code}]")
                try:
                    print(f"Детали: {response.json().get('detail')}")
                except:
                    print(f"Ответ: {response.text[:200]}")
        except Exception as e:
            print(f"[Ошибка подключения] {e}")

    def login(self):
        print("\n--- Вход в систему ---")
        username = input("Введите логин: ")
        password = input("Введите пароль: ")

        try:
            # Сначала проверяем пароль на сервере
            payload = {
                "username": username,
                "password": password,
                "public_key": ""
            }
            resp = requests.post(f"{BASE_URL}/verify_user", json=payload, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                self.username = username
                self.user_id = data["id"]

                # После успешной проверки на сервере пытаемся загрузить ключи
                if self._load_keys():
                    print(f"[Успех] Добро пожаловать, {username}! (ID: {self.user_id})")
                else:
                    print(f"[Предупреждение] Приватный ключ для {username} не найден в {KEYS_DIR}.")
                    print("Вы зашли в систему, но не сможете расшифровать сообщения.")
            else:
                print(f"[Ошибка] {resp.json().get('detail', 'Неверный логин или пароль')}")
                self.username = None
                self.user_id = None
        except Exception as e:
            print(f"[Ошибка подключения] {e}")
            self.username = None

    def send_message(self):
        if not self.user_id:
            print("Сначала войдите в систему!")
            return

        recipient_name = input("Кому отправить (логин): ")

        # 1. Получаем ID и публичный ключ получателя
        try:
            resp = requests.get(f"{BASE_URL}/users/{recipient_name}/public_key", timeout=5)
            if resp.status_code != 200:
                print("[Ошибка] Получатель не найден.")
                return

            recipient_data = resp.json()
            recipient_pub_key = recipient_data["public_key"].encode('utf-8')
            recipient_id = recipient_data["id"]

            # 2. Пишем сообщение
            message_text = input("Введите сообщение: ")

            # 3. Шифруем (Логика отобразится в логах CryptoEngine)
            # Шифруем для получателя И для себя
            encrypted_package = CryptoEngine.encrypt_message(message_text, recipient_pub_key, self.public_key)

            # 4. Отправляем пакет
            payload = {
                "sender_id": self.user_id,
                "recipient_id": recipient_id,
                "encrypted_content": encrypted_package["encrypted_content"],
                "encrypted_session_key": encrypted_package["encrypted_session_key"],
                "encrypted_session_key_sender": encrypted_package["encrypted_session_key_sender"],
                "iv": encrypted_package["iv"],
                "integrity_hash": encrypted_package["integrity_hash"]
            }

            res = requests.post(f"{BASE_URL}/send_message", json=payload, timeout=10)
            if res.status_code == 200:
                print(f"[ОК] Зашифрованное сообщение для {recipient_name} (ID {recipient_id}) отправлено.")
        except Exception as e:
            print(f"[Ошибка] {e}")

    def check_inbox(self):
        if not self.user_id:
            print("Сначала войдите в систему!")
            return

        print(f"\n--- Входящие для {self.username} (ID: {self.user_id}) ---")
        try:
            resp = requests.get(f"{BASE_URL}/messages/{self.user_id}", timeout=10)
            messages = resp.json()

            if not messages:
                print("Сообщений нет.")
                return

            for m in messages:
                if m['sender_id'] == self.user_id:
                    role = "ОТПРАВЛЕНО (вам)"
                    session_key = m.get('encrypted_session_key_sender')
                    target = f"Кому: ID {m['recipient_id']}"
                else:
                    role = "ВХОДЯЩЕЕ"
                    session_key = m.get('encrypted_session_key')
                    target = f"От: ID {m['sender_id']}"

                print(f"\n[{role} | {target}]")
                if not session_key:
                    print(">>> [Ошибка: ключ для вас не найден]")
                    continue

                pkg = {
                    "encrypted_content": m["encrypted_content"],
                    "encrypted_session_key": session_key,
                    "iv": m["iv"],
                    "integrity_hash": m["integrity_hash"]
                }
                # Дешифровка
                try:
                    decrypted_text, integrity = CryptoEngine.decrypt_message(pkg, self.private_key)
                    if integrity:
                        print(f">>> {decrypted_text} [ЦЕЛОСТНОСТЬ OK]")
                    else:
                        print(f">>> {decrypted_text} [ОШИБКА: ДАННЫЕ ИЗМЕНЕНЫ]")
                except:
                    print(">>> [Ошибка дешифровки]")
        except Exception as e:
            print(f"[Ошибка] {e}")


def main():
    client = SecureClient()
    while True:
        if client.username:
            key_status = "" if client.private_key else " [НЕТ КЛЮЧА]"
            status = f"(Вы: {client.username}{key_status})"
        else:
            status = "(Не в сети)"
        print(f"\nMessenger {status}")
        print("1. Регистрация\n2. Вход\n3. Отправить сообщение\n4. Проверить почту\n5. Выход")
        choice = input("Выберите действие: ")

        if choice == "1":
            client.register()
        elif choice == "2":
            client.login()
        elif choice == "3":
            client.send_message()
        elif choice == "4":
            client.check_inbox()
        elif choice == "5":
            break
        else:
            print("Неверный ввод.")


if __name__ == "__main__":
    main()
