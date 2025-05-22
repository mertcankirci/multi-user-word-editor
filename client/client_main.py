# client/client_main.py

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import socket
import threading
from shared.messages import parse_message, create_message, USER_LIST, FILE_LIST, FILE_SYNC

# === İstemci Ayarları ===
HOST = '127.0.0.1'
PORT = 5000


def receive_messages(sock):
    while True:
        try:
            data = sock.recv(4096).decode()
            if not data:
                break
            command, args, body = parse_message(data)

            if command == USER_LIST:
                print("\n[Bağlı Kullanıcılar]", ', '.join(args))

            elif command == FILE_LIST:
                print("\n[Mevcut Dosyalar]", ', '.join(args))

            elif command == FILE_SYNC:
                filename = args[0]
                print(f"\n[{filename} Güncellendi] ->\n{body}")

            else:
                print(f"[GELEN MESAJ] {command} {args} {body}")

        except Exception as e:
            print(f"[HATA] {e}")
            break


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((HOST, PORT))

        username = input("Kullanıcı adınızı girin: ")
        login_msg = create_message("LOGIN", username)
        sock.sendall(login_msg.encode())

        threading.Thread(target=receive_messages, args=(sock,), daemon=True).start()

        while True:
            print("\nKomutlar: CREATE, JOIN, UPDATE, QUIT")
            cmd = input("Komut girin: ").strip().upper()

            if cmd == "CREATE":
                filename = input("Dosya adı: ")
                msg = create_message("FILE_CREATE", filename)
                sock.sendall(msg.encode())

            elif cmd == "JOIN":
                filename = input("Düzenlenecek dosya: ")
                msg = create_message("FILE_JOIN", filename)
                sock.sendall(msg.encode())

            elif cmd == "UPDATE":
                filename = input("Dosya adı: ")
                line = input("Satır numarası: ")
                content = input("Yeni içerik: ")
                msg = create_message("FILE_UPDATE", filename, line, body=content)
                sock.sendall(msg.encode())

            elif cmd == "QUIT":
                msg = create_message("QUIT", username)
                sock.sendall(msg.encode())
                break

            else:
                print("[UYARI] Geçersiz komut.")


if __name__ == '__main__':
    main()