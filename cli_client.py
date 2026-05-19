import tkinter as tk
from tkinter import messagebox, ttk, simpledialog, filedialog
import requests
import threading
import time
import os
from datetime import datetime
from backend.crypto_engine import CryptoEngine

KEYS_DIR = "keys"


class MessengerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Messenger")
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

        self.init_styles()
        self.setup_login_screen()

    def init_styles(self):
        self.style = ttk.Style()
        # self.style.theme_use('clam') # Usually looks better than default on Windows/Linux

        # Colors
        PRIMARY = "#2c3e50"
        SECONDARY = "#34495e"
        ACCENT = "#3498db"
        BG_LIGHT = "#ecf0f1"
        TEXT_COLOR = "#2c3e50"

        self.style.configure(".", font=("Segoe UI", 10))
        self.style.configure("TFrame", background=BG_LIGHT)
        self.style.configure("TLabel", background=BG_LIGHT, foreground=TEXT_COLOR)
        self.style.configure("Header.TLabel", font=("Segoe UI", 18, "bold"), foreground=PRIMARY)
        self.style.configure("Subheader.TLabel", font=("Segoe UI", 12, "bold"), foreground=SECONDARY)

        self.style.configure("Action.TButton", padding=6, font=("Segoe UI", 10, "bold"))
        self.style.configure("Accent.TButton", background=ACCENT, foreground="white")

        self.root.configure(bg=BG_LIGHT)

    def setup_login_screen(self):
        self.clear_screen()
        self.root.geometry("450x500")

        main_frame = ttk.Frame(self.root, padding="40")
        main_frame.pack(expand=True, fill="both")

        ttk.Label(main_frame, text="Messenger", style="Header.TLabel").pack(pady=(0, 20))

        form_frame = ttk.Frame(main_frame)
        form_frame.pack(fill="x")

        ttk.Label(form_frame, text="IP Сервера:", font=("Segoe UI", 10)).pack(anchor="w", pady=(10, 0))
        self.ip_entry = ttk.Entry(form_frame, font=("Segoe UI", 11))
        self.ip_entry.insert(0, "127.0.0.1")
        self.ip_entry.pack(fill="x", pady=5)

        ttk.Label(form_frame, text="Логин:", font=("Segoe UI", 10)).pack(anchor="w", pady=(10, 0))
        self.user_entry = ttk.Entry(form_frame, font=("Segoe UI", 11))
        self.user_entry.pack(fill="x", pady=5)

        ttk.Label(form_frame, text="Пароль:", font=("Segoe UI", 10)).pack(anchor="w", pady=(10, 0))
        self.pass_entry = ttk.Entry(form_frame, show="*", font=("Segoe UI", 11))
        self.pass_entry.pack(fill="x", pady=5)

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=25)

        ttk.Button(btn_frame, text="Войти", style="Action.TButton", command=self.login).pack(fill="x", pady=5)
        ttk.Button(btn_frame, text="Создать аккаунт", style="Action.TButton", command=self.register).pack(fill="x",
                                                                                                          pady=5)

    def setup_chat_screen(self):
        self.clear_screen()
        self.root.geometry("1000x700")

        # Главный контейнер
        self.paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.paned.pack(fill="both", expand=True)

        # --- ЛЕВАЯ ПАНЕЛЬ (Контакты) ---
        self.contacts_frame = ttk.Frame(self.paned, padding="10", width=250)
        self.paned.add(self.contacts_frame, weight=1)

        ttk.Label(self.contacts_frame, text="Чаты", style="Subheader.TLabel").pack(pady=(0, 10), anchor="w")

        self.contacts_listbox = tk.Listbox(
            self.contacts_frame,
            font=("Segoe UI", 11),
            bg="white",
            fg="#2c3e50",
            selectbackground="#3498db",
            selectforeground="white",
            borderwidth=0,
            highlightthickness=1,
            highlightbackground="#bdc3c7"
        )
        self.contacts_listbox.pack(fill="both", expand=True)
        self.contacts_listbox.bind("<<ListboxSelect>>", self.on_contact_select)

        new_chat_btn = ttk.Button(self.contacts_frame, text="+ Начать чат", command=self.start_new_chat)
        new_chat_btn.pack(fill="x", pady=(10, 0))

        ttk.Frame(self.contacts_frame, height=20).pack()  # Spacer

        user_info = ttk.Frame(self.contacts_frame)
        user_info.pack(fill="x", side="bottom")

        ttk.Separator(user_info, orient="horizontal").pack(fill="x", pady=10)
        ttk.Label(user_info, text=f"Аккаунт: {self.username}", font=("Segoe UI", 9)).pack(anchor="w")
        ttk.Button(user_info, text="Выйти", command=self.logout).pack(fill="x", pady=5)

        # --- ПРАВАЯ ПАНЕЛЬ (Окно чата) ---
        self.chat_container = ttk.Frame(self.paned, padding="15")
        self.paned.add(self.chat_container, weight=4)

        self.chat_header = ttk.Label(self.chat_container, text="Выберите собеседника", style="Subheader.TLabel")
        self.chat_header.pack(fill="x", pady=(0, 15))

        # Текстовое поле с тегами для разного оформления
        self.chat_display = tk.Text(
            self.chat_container,
            state="disabled",
            wrap="word",
            font=("Segoe UI", 11),
            bg="#fdfdfd",
            padx=10,
            pady=10,
            borderwidth=1,
            highlightthickness=0,
            relief="flat"
        )
        self.chat_display.pack(fill="both", expand=True)

        # Настройка тегов для "пузырей" сообщений
        self.chat_display.tag_configure("me_header", foreground="#3498db", font=("Segoe UI", 10, "bold"))
        self.chat_display.tag_configure("other_header", foreground="#e67e22", font=("Segoe UI", 10, "bold"))
        self.chat_display.tag_configure("timestamp", foreground="#95a5a6", font=("Segoe UI", 9))
        self.chat_display.tag_configure("message_body", lmargin1=20, lmargin2=20, spacing3=10)
        self.chat_display.tag_configure("file_link", foreground="#3498db", underline=True)

        self.input_parent = ttk.Frame(self.chat_container, padding=(0, 15, 0, 0))
        self.input_parent.pack(fill="x", side="bottom")

        self.msg_entry = ttk.Entry(self.input_parent, font=("Segoe UI", 11))
        self.msg_entry.pack(side="left", fill="x", expand=True, ipady=5)
        self.msg_entry.bind("<Return>", lambda e: self.send_message())

        self.send_btn = ttk.Button(self.input_parent, text="Отправить", command=self.send_message)
        self.send_btn.pack(side="right", padx=(10, 0))

        self.file_btn = ttk.Button(self.input_parent, text="📎", width=4, command=self.send_file)
        self.file_btn.pack(side="right", padx=(5, 0))

        # Потоки
        self.stop_thread = False
        if not hasattr(self, 'polling_active') or not self.polling_active:
            self.polling_active = True
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
        for m in messages:
            sender = m["sender"]
            text = m["text"]
            status = m["status"]
            file_name = m.get("file_name")

            if sender == "me":
                header_tag = "me_header"
                header_text = "Вы"
            else:
                header_tag = "other_header"
                header_text = self.id_to_name.get(sender, f"ID {sender}")

            # Вставляем заголовок (имя отправителя) и время
            timestamp = m.get("timestamp", "")
            self.chat_display.insert(tk.END, f"{header_text} ", header_tag)
            self.chat_display.insert(tk.END, f"{timestamp}\n", "timestamp")

            if file_name:
                display_text = f"📎 {file_name}"
                tag_name = f"file_{m['id']}"

                self.chat_display.insert(tk.END, display_text, (tag_name, "file_link", "message_body"))
                self.chat_display.insert(tk.END, f" ({m['file_size']} байт){status}\n", "message_body")

                self.chat_display.tag_bind(tag_name, "<Button-1>", lambda e, msg=m: self.download_file(msg))
            else:
                self.chat_display.insert(tk.END, f"{text}{status}\n", "message_body")

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
                with open(pub_path, "rb") as f:
                    self.public_key = f.read()
            else:
                # Derive public key from private if missing
                try:
                    self.public_key = CryptoEngine.get_public_key_from_private(self.private_key)
                    # Save it for future use
                    with open(pub_path, "wb") as f:
                        f.write(self.public_key)
                except Exception as e:
                    print(f"Error deriving public key: {e}")
                    self.public_key = None
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
                self.public_key = pub  # Сохраняем публичный ключ в памяти
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

            if not self.public_key:
                messagebox.showwarning("Внимание",
                                       "Ваш публичный ключ не загружен. Вы не сможете прочитать это сообщение позже.")

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

    def send_file(self):
        if self.current_chat_id is None:
            messagebox.showwarning("Внимание", "Выберите чат из списка слева")
            return

        file_path = filedialog.askopenfilename()
        if not file_path:
            return

        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)

        if file_size > 10 * 1024 * 1024:
            messagebox.showwarning("Внимание", "Файл слишком велик (макс 10МБ)")
            return

        try:
            with open(file_path, "rb") as f:
                file_data = f.read()

            recipient_name = self.id_to_name.get(self.current_chat_id)
            r_resp = requests.get(f"{self.base_url}/users/{recipient_name}/public_key", timeout=5)
            if r_resp.status_code != 200:
                messagebox.showerror("Ошибка", "Не удалось получить ключ получателя")
                return

            r_data = r_resp.json()
            r_pub = r_data["public_key"].encode('utf-8')

            if not self.public_key:
                messagebox.showwarning("Внимание",
                                       "Ваш публичный ключ не загружен. Вы не сможете скачать этот файл позже.")

            # Шифруем файл
            pkg = CryptoEngine.encrypt_data(file_data, r_pub, self.public_key)
            payload = {
                "sender_id": self.user_id,
                "recipient_id": self.current_chat_id,
                "file_name": file_name,
                "file_size": file_size,
                **pkg
            }
            s_resp = requests.post(f"{self.base_url}/send_message", json=payload, timeout=10)
            if s_resp.status_code == 200:
                messagebox.showinfo("Успех", f"Файл {file_name} отправлен")
            else:
                messagebox.showerror("Ошибка", "Не удалось отправить файл")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def download_file(self, msg_data):
        if not self.private_key:
            messagebox.showerror("Ошибка", "Нет приватного ключа для дешифровки")
            return

        file_name = msg_data.get("file_name")
        raw_pkg = msg_data.get("raw_pkg")

        # Decide which session key to use
        # Check if current user is sender
        if str(raw_pkg["sender_id"]) == str(self.user_id):
            session_key_hex = raw_pkg.get("encrypted_session_key_sender")
        else:
            session_key_hex = raw_pkg.get("encrypted_session_key")

        if not session_key_hex:
            messagebox.showerror("Ошибка", "Ключ сессии не найден")
            return

        save_path = filedialog.asksaveasfilename(initialfile=file_name)
        if not save_path:
            return

        try:
            pkg = {
                "encrypted_content": raw_pkg["encrypted_content"],
                "encrypted_session_key": session_key_hex,
                "iv": raw_pkg["iv"],
                "integrity_hash": raw_pkg["integrity_hash"]
            }
            data, ok = CryptoEngine.decrypt_data(pkg, self.private_key)
            if not ok:
                messagebox.showwarning("Внимание", "Целостность файла нарушена!")

            with open(save_path, "wb") as f:
                f.write(data)

            messagebox.showinfo("Успех", f"Файл сохранен в {save_path}")
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

                    # Форматирование времени
                    try:
                        sent_at = datetime.fromisoformat(m["sent_at"].replace('Z', '+00:00'))
                        # Конвертируем в локальное время (сервер обычно шлет UTC)
                        local_dt = sent_at.astimezone()
                        now = datetime.now()
                        if local_dt.date() == now.date():
                            fmt_time = local_dt.strftime("%H:%M")
                        else:
                            fmt_time = local_dt.strftime("%d.%m.%y %H:%M")
                    except:
                        fmt_time = ""

                    msg_data = {
                        "id": msg_id,
                        "sender": sender_label,
                        "status": "",
                        "timestamp": fmt_time,
                        "file_name": m.get("file_name"),
                        "file_size": m.get("file_size"),
                        "raw_pkg": m  # save full package for decryption/download
                    }

                    if not self.private_key:
                        msg_data["text"] = "[Шифровано - нет ключа]"
                    else:
                        session_key = m.get(session_key_field)
                        if not session_key:
                            msg_data["text"] = "[Ошибка: ключ для вас не найден]"
                        else:
                            pkg = {
                                "encrypted_content": m["encrypted_content"],
                                "encrypted_session_key": session_key,
                                "iv": m["iv"],
                                "integrity_hash": m["integrity_hash"]
                            }
                            try:
                                # If it's a file, we can show size etc but decryption is for download
                                if m.get("file_name"):
                                    msg_data["text"] = f"Файл: {m['file_name']} ({m['file_size']} байт)"
                                else:
                                    data, ok = CryptoEngine.decrypt_data(pkg, self.private_key)
                                    text = data.decode()
                                    msg_data["text"] = text
                                    if not ok: msg_data["status"] = " [!] Защита нарушена"
                            except Exception as e:
                                msg_data["text"] = "[Ошибка дешифровки]"

                    self.chats[target_id].append(msg_data)
                    self.processed_msg_ids.add(msg_id)
                    new_data_received = True

                if new_data_received:
                    self.update_contacts_list()
                    if self.current_chat_id is not None:
                        self.refresh_chat_display()

            except Exception as e:
                print(f"Poll error: {e}")

            if self.stop_thread: break
            time.sleep(3)

        self.polling_active = False


if __name__ == "__main__":
    root = tk.Tk()
    app = MessengerGUI(root)
    root.mainloop()
