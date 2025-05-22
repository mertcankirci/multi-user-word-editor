# client/gui.py

import tkinter as tk
from tkinter import simpledialog, messagebox
import threading
import socket
import sys 
import os 
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.messages import create_message, parse_message, FILE_LIST, FILE_SYNC, USER_LIST

HOST = '127.0.0.1'
PORT = 5000

class TextEditorClient:
    def __init__(self, master):
        self.master = master
        self.master.title("Çok Kullanıcılı Metin Editörü")

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.username = simpledialog.askstring("Kullanıcı Adı", "Lütfen kullanıcı adınızı girin:")
        self.current_file = None

        # Sol panel: Kullanıcı listesi
        left_frame = tk.Frame(master)
        left_frame.pack(side=tk.LEFT, fill=tk.Y)

        self.user_listbox = tk.Listbox(left_frame)
        self.user_listbox.pack(side=tk.LEFT, fill=tk.Y)

        right_frame = tk.Frame(master)
        right_frame.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH)

        self.file_var = tk.StringVar()
        self.file_dropdown = tk.OptionMenu(right_frame, self.file_var, [])
        self.file_dropdown.pack(fill=tk.X)

        self.text_area = tk.Text(right_frame, wrap=tk.WORD)
        self.text_area.pack(expand=True, fill=tk.BOTH)

        # Sadece metin değişikliği izleyicisi
        self.text_area.bind('<<Modified>>', self.on_text_modified)
        self.last_update = 0

        button_frame = tk.Frame(right_frame)
        button_frame.pack(fill=tk.X)

        tk.Button(button_frame, text="Dosya Oluştur", command=self.create_file).pack(side=tk.LEFT)
        tk.Button(button_frame, text="Dosyayı Aç (JOIN)", command=self.join_file).pack(side=tk.LEFT)
        tk.Button(button_frame, text="Kaydet (UPDATE)", command=self.update_file).pack(side=tk.LEFT)
        tk.Button(button_frame, text="Çıkış", command=self.quit_app).pack(side=tk.RIGHT)

        self.connected = True  # Bağlantı durumunu takip etmek için
        self.connect_to_server()
        threading.Thread(target=self.receive_messages, daemon=True).start()

    def connect_to_server(self):
        try:
            self.sock.connect((HOST, PORT))
            login_msg = create_message("LOGIN", self.username)
            self.sock.sendall(login_msg.encode())
        except Exception as e:
            messagebox.showerror("Bağlantı Hatası", str(e))
            self.master.destroy()

    def receive_messages(self):
        while True:
            try:
                data = self.sock.recv(4096).decode()
                if not data:
                    break
                command, args, body = parse_message(data)

                if command == FILE_LIST:
                    self.master.after(0, self.update_file_list, args)

                elif command == FILE_SYNC:
                    self.current_file = args[0]
                    self.text_area.delete(1.0, tk.END)
                    if body:
                        self.text_area.insert(tk.END, body)

                elif command == USER_LIST:
                    self.master.after(0, self.update_user_list, args)

            except Exception as e:
                print(f"[HATA] {e}")
                break

    def update_user_list(self, users):
        self.user_listbox.delete(0, tk.END)
        for user in users:
            self.user_listbox.insert(tk.END, user)

    def update_file_list(self, files):
        self.file_dropdown['menu'].delete(0, 'end')
        for fname in files:
            self.file_dropdown['menu'].add_command(label=fname, command=lambda f=fname: self.file_var.set(f))
        if files:
            self.file_var.set(files[0])

    def send_message(self, msg):
        """Güvenli mesaj gönderme fonksiyonu"""
        if not self.connected:
            return False
        try:
            self.sock.sendall(msg.encode())
            return True
        except (BrokenPipeError, ConnectionResetError):
            self.connected = False
            messagebox.showerror("Bağlantı Hatası", "Sunucu bağlantısı koptu!")
            self.master.destroy()
            return False

    def on_text_modified(self, event=None):
        if not self.current_file or not self.connected:
            return

        # Metin alanının değişiklik bayrağını sıfırla
        self.text_area.edit_modified(False)

        # Çok sık güncelleme yapmamak için 0.5 saniye bekle
        current_time = time.time()
        if current_time - self.last_update < 0.5:
            return

        self.last_update = current_time
        self.update_content()

    def update_content(self):
        """İçeriği güncelleme işlemini tek bir fonksiyonda topla"""
        content = self.text_area.get(1.0, tk.END).strip()
        if not content:
            return

        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            msg = create_message("FILE_UPDATE", self.current_file, str(i), body=line)
            if not self.send_message(msg):
                return

    def update_file(self):
        if not self.current_file or not self.connected:
            messagebox.showwarning("Uyarı", "Önce bir dosya açmalısınız (JOIN).")
            return

        content = self.text_area.get(1.0, tk.END).strip()
        if not content:
            return

        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            msg = create_message("FILE_UPDATE", self.current_file, str(i), body=line)
            if not self.send_message(msg):
                return

    def create_file(self):
        fname = simpledialog.askstring("Dosya Oluştur", "Yeni dosya adı:")
        if fname:
            msg = create_message("FILE_CREATE", fname)
            self.send_message(msg)

    def join_file(self):
        fname = self.file_var.get()
        if fname:
            self.current_file = fname
            msg = create_message("FILE_JOIN", fname)
            self.send_message(msg)

    def quit_app(self):
        try:
            if self.connected:
                quit_msg = create_message("QUIT", self.username)
                self.send_message(quit_msg)
        except:
            pass
        self.sock.close()
        self.master.destroy()


def main():
    root = tk.Tk()
    app = TextEditorClient(root)
    root.mainloop()


if __name__ == '__main__':
    main()
