import tkinter as tk
from tkinter import messagebox, ttk, simpledialog
import requests
import threading
import time
import os
from backend.crypto_engine import CryptoEngine

KEYS_DIR = "keys"


class MessengerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Secure Messenger")
        self.root.geometry("900x600")

        self.username = None
        self.user_id = None
        self.private_key = None
        self.public_key = None
        self.base_url = "http://127.0.0.1:8000"

        # Данные для чатов
        self.chats = {}  # {target_user_id: [messages]}
        self.id_to_name = {}  # {user_id: username}
        self.current_chat_id = None

        if not os.path.exists(KEYS_DIR):
            os.makedirs(KEYS_DIR)

        self.setup_login_screen()

    def setup_login_screen(self):
        self.clear_screen()
        self.root.geometry("400x400")

        frame = ttk.Frame(self.root, padding="20")
        frame.pack(expand=True)

        ttk.Label(frame, text="Secure Messenger", font=("Arial", 16, "bold")).grid(row=0, column=0, columnspan=2,
                                                                                   pady=10)

        ttk.Label(frame, text="IP Сервера:").grid(row=1, column=0, sticky="e", pady=5)
        self.ip_entry = ttk.Entry(frame)
        self.ip_entry.insert(0, "127.0.0.1")
        self.ip_entry.grid(row=1, column=1, pady=5)

        ttk.Label(frame, text="Логин:").grid(row=2, column=0, sticky="e", pady=5)
        self.user_entry = ttk.Entry(frame)
        self.user_entry.grid(row=2, column=1, pady=5)

        ttk.Label(frame, text="Пароль:").grid(row=3, column=0, sticky="e", pady=5)
        self.pass_entry = ttk.Entry(frame, show="*")
        self.pass_entry.grid(row=3, column=1, pady=5)

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=15)

        ttk.Button(btn_frame, text="Войти", command=self.login).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Регистрация", command=self.register).pack(side="left", padx=5)

    def setup_chat_screen(self):
        self.clear_screen()
        self.root.geometry("900x600")

        # Главный контейнер (Слева список, Справа чат)
        self.paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.paned.pack(fill="both", expand=True)

        # --- ЛЕВАЯ ПАНЕЛЬ (Контакты) ---
        self.contacts_frame = ttk.Frame(self.paned, padding="5", width=200)
        self.paned.add(self.contacts_frame, weight=1)

        ttk.Label(self.contacts_frame, text="Чаты", font=("Arial", 12, "bold")).pack(pady=5)

        self.contacts_listbox = tk.Listbox(self.contacts_frame, font=("Arial", 10))
        self.contacts_listbox.pack(fill="both", expand=True)
        self.contacts_listbox.bind("<<ListboxSelect>>", self.on_contact_select)

        new_chat_btn = ttk.Button(self.contacts_frame, text="+ Новый чат", command=self.start_new_chat)
        new_chat_btn.pack(fill="x", pady=5)

        ttk.Separator(self.contacts_frame, orient="horizontal").pack(fill="x", pady=5)
        ttk.Label(self.contacts_frame, text=f"Вы: {self.username}").pack()
        ttk.Button(self.contacts_frame, text="Выйти", command=self.logout).pack(fill="x", pady=5)

        # --- ПРАВАЯ ПАНЕЛЬ (Окно чата) ---
        self.main_chat_frame = ttk.Frame(self.paned, padding="10")
        self.paned.add(self.main_chat_frame, weight=4)

        self.chat_header = ttk.Label(self.main_chat_frame, text="Выберите чат...", font=("Arial", 12, "bold"))
        self.chat_header.pack(fill="x", pady=(0, 10))

        self.chat_display = tk.Text(self.main_chat_frame, state="disabled", wrap="word", font=("Arial", 10))
        self.chat_display.pack(fill="both", expand=True)

        self.input_frame = ttk.Frame(self.main_chat_frame)
        self.input_frame.pack(fill="x", pady=(10, 0))

        self.msg_entry = ttk.Entry(self.input_frame)
        self.msg_entry.pack(side="left", fill="x", expand=True)
        self.msg_entry.bind("<Return>", lambda e: self.send_message())

        self.send_btn = ttk.Button(self.input_frame, text="Отправить", command=self.send_message)
        self.send_btn.pack(side="right", padx=(5, 0))

        # Потоки
        self.stop_thread = False
        threading.Thread(target=self.poll_messages, daemon=True).start()

    def clear_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def logout(self):
        self.stop_thread = True
        self.username = None
        self.user_id = None
        self.chats = {}
        self.id_to_name = {}
        self.current_chat_id = None
        self.setup_login_screen()

    def on_contact_select(self, event):
        selection = self.contacts_listbox.curselection()
        if not selection:
            return

        index = selection[0]
        if hasattr(self, 'contacts_ids') and index < len(self.contacts_ids):
            self.current_chat_id = self.contacts_ids[index]
            self.refresh_chat_display()

    def refresh_chat_display(self):
        self.chat_display.config(state="normal")
        self.chat_display.delete('1.0', tk.END)

        name = self.id_to_name.get(self.current_chat_id, f"ID {self.current_chat_id}")
        self.chat_header.config(text=f"Чат с {name}")

        messages = self.chats.get(self.current_chat_id, [])
        for sender, text, status in messages:
            # sender может быть "me" или ID отправителя
            if sender == "me":
                prefix = "Вы: "
            else:
                s_name = self.id_to_name.get(sender, f"ID {sender}")
                prefix = f"{s_name}: "
            self.chat_display.insert(tk.END, f"{prefix}{text}{status}\n")

        self.chat_display.see(tk.END)
        self.chat_display.config(state="disabled")

    def start_new_chat(self):
        recipient_name = simpledialog.askstring("Новый чат", "Введите логин пользователя:")
        if not recipient_name:
            return

        try:
            resp = requests.get(f"{self.base_url}/users/{recipient_name}/public_key", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                uid = data["id"]
                self.id_to_name[uid] = recipient_name
                if uid not in self.chats:
                    self.chats[uid] = []
                    self.update_contacts_list()

                # Переключаемся на этот чат
                self.current_chat_id = uid
                self.refresh_chat_display()
            else:
                messagebox.showerror("Ошибка", "Пользователь не найден")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def update_contacts_list(self):
        self.contacts_listbox.delete(0, tk.END)
        self.contacts_ids = sorted(self.chats.keys())

        for uid in self.contacts_ids:
            name = self.id_to_name.get(uid, f"ID {uid}")
            self.contacts_listbox.insert(tk.END, name)

    def _load_keys(self):
        priv_path = os.path.join(KEYS_DIR, f"{self.username}_private.pem")
        pub_path = os.path.join(KEYS_DIR, f"{self.username}_public.pem")
        if os.path.exists(priv_path):
            with open(priv_path, "rb") as f:
                self.private_key = f.read()
            if os.path.exists(pub_path):
                with open(pub_path, "rb") as f: self.public_key = f.read()
            return True
        return False

    def _save_keys(self, priv, pub):
        priv_path = os.path.join(KEYS_DIR, f"{self.username}_private.pem")
        pub_path = os.path.join(KEYS_DIR, f"{self.username}_public.pem")
        with open(priv_path, "wb") as f: f.write(priv)
        with open(pub_path, "wb") as f: f.write(pub)

    def login(self):
        self.base_url = f"http://{self.ip_entry.get()}:8000"
        username = self.user_entry.get()
        password = self.pass_entry.get()

        try:
            resp = requests.post(f"{self.base_url}/verify_user",
                                 json={"username": username, "password": password, "public_key": ""},
                                 timeout=5)
            if resp.status_code == 200:
                self.username = username
                self.user_id = resp.json()["id"]
                if self._load_keys():
                    self.setup_chat_screen()
                else:
                    messagebox.showwarning("Внимание", "Ключ не найден локально. Вы не сможете читать сообщения.")
                    self.setup_chat_screen()
            else:
                messagebox.showerror("Ошибка", resp.json().get("detail", "Сбой входа"))
        except Exception as e:
            messagebox.showerror("Ошибка подключения", str(e))

    def register(self):
        self.base_url = f"http://{self.ip_entry.get()}:8000"
        username = self.user_entry.get()
        password = self.pass_entry.get()

        if not username or not password:
            messagebox.showwarning("Внимание", "Введите логин и пароль")
            return

        priv, pub = CryptoEngine.generate_rsa_keypair()
        try:
            resp = requests.post(f"{self.base_url}/register",
                                 json={"username": username, "password": password, "public_key": pub.decode('utf-8')},
                                 timeout=10)
            if resp.status_code == 200:
                self.username = username
                self.user_id = resp.json()["id"]
                self.private_key = priv
                self._save_keys(priv, pub)
                messagebox.showinfo("Успех", f"Зарегистрирован! ID: {self.user_id}")
                self.setup_chat_screen()
            else:
                messagebox.showerror("Ошибка", resp.json().get("detail"))
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def send_message(self):
        if self.current_chat_id is None:
            messagebox.showwarning("Внимание", "Выберите чат из списка слева")
            return

        text = self.msg_entry.get()
        if not text: return

        try:
            # Получаем ключ (мог измениться или новый сеанс)
            recipient_name = self.id_to_name.get(self.current_chat_id)

            r_resp = requests.get(f"{self.base_url}/users/{recipient_name}/public_key", timeout=5)
            if r_resp.status_code != 200:
                messagebox.showerror("Ошибка", "Не удалось получить ключ получателя")
                return

            r_data = r_resp.json()
            r_pub = r_data["public_key"].encode('utf-8')

            # Шифруем для получателя И для себя
            pkg = CryptoEngine.encrypt_message(text, r_pub, self.public_key)
            payload = {
                "sender_id": self.user_id,
                "recipient_id": self.current_chat_id,
                **pkg
            }
            s_resp = requests.post(f"{self.base_url}/send_message", json=payload, timeout=5)
            if s_resp.status_code == 200:
                # Очищаем поле ввода. Сообщение появится в чате после поллинга от сервера.
                self.msg_entry.delete(0, tk.END)
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def poll_messages(self):
        self.processed_msg_ids = set()

        while not self.stop_thread:
            try:
                resp = requests.get(f"{self.base_url}/messages/{self.user_id}", timeout=5)
                messages = resp.json()

                new_data_received = False
                for m in messages:
                    msg_id = m.get('id')
                    if msg_id in self.processed_msg_ids:
                        continue

                    # Определяем, с кем переписка
                    if m['sender_id'] == self.user_id:
                        # Мы отправитель
                        target_id = m['recipient_id']
                        session_key_field = "encrypted_session_key_sender"
                        sender_label = "me"
                    else:
                        # Мы получатель
                        target_id = m['sender_id']
                        session_key_field = "encrypted_session_key"
                        sender_label = target_id

                    # Пытаемся узнать имя контакта, если не знаем
                    if target_id not in self.id_to_name:
                        try:
                            n_resp = requests.get(f"{self.base_url}/users/by-id/{target_id}", timeout=2)
                            if n_resp.status_code == 200:
                                self.id_to_name[target_id] = n_resp.json()["username"]
                        except:
                            pass

                    if target_id not in self.chats:
                        self.chats[target_id] = []
                        new_data_received = True

                    if not self.private_key:
                        self.chats[target_id].append((sender_label, "[Шифровано - нет ключа]", ""))
                    else:
                        session_key = m.get(session_key_field)
                        if not session_key:
                            self.chats[target_id].append((sender_label, "[Ошибка: ключ для вас не найден]", ""))
                        else:
                            pkg = {
                                "encrypted_content": m["encrypted_content"],
                                "encrypted_session_key": session_key,
                                "iv": m["iv"],
                                "integrity_hash": m["integrity_hash"]
                            }
                            try:
                                text, ok = CryptoEngine.decrypt_message(pkg, self.private_key)
                                status = "" if ok else " [!] Ошибка целостности"
                                self.chats[target_id].append((sender_label, text, status))
                            except:
                                self.chats[target_id].append((sender_label, "[Ошибка дешифровки]", ""))

                    self.processed_msg_ids.add(msg_id)
                    new_data_received = True

                if new_data_received:
                    self.update_contacts_list()
                    if self.current_chat_id is not None:
                        self.refresh_chat_display()

            except Exception as e:
                print(f"Poll error: {e}")

            time.sleep(3)


if __name__ == "__main__":
    root = tk.Tk()
    app = MessengerGUI(root)
    root.mainloop()
