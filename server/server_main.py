# server/server_main.py

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from server.file_manager import background_auto_save


import socket
import threading
from shared.messages import parse_message, create_message, LOGIN, USER_LIST, FILE_LIST, FILE_CREATE, FILE_JOIN, FILE_UPDATE, FILE_SYNC, QUIT

# === Sunucu Ayarları ===
HOST = '127.0.0.1'
PORT = 5000

clients = {}  # socket -> username
usernames = set()
files = {}  # filename -> list of lines

def broadcast_all(message, exclude_sock=None):
    for client_sock in clients:
        if client_sock != exclude_sock:
            try:
                client_sock.sendall(message.encode())
            except:
                continue

def handle_client(client_sock):
    username = None
    with client_sock:
        while True:
            try:
                data = client_sock.recv(4096).decode()
                if not data:
                    break
                    
                # Birden fazla mesaj olabilir, her birini ayrı ayrı işle
                messages = parse_multiple_messages(data)
                for message in messages:
                    command, args, body = parse_message(message)

                    if command == LOGIN:
                        username = args[0]
                        clients[client_sock] = username
                        usernames.add(username)
                        user_list_msg = create_message(USER_LIST, *usernames)
                        broadcast_all(user_list_msg)

                    elif command == FILE_CREATE:
                        filename = args[0]
                        if filename not in files:
                            files[filename] = []
                        file_list_msg = create_message(FILE_LIST, *files.keys())
                        broadcast_all(file_list_msg)

                    elif command == FILE_JOIN:
                        filename = args[0]
                        content = "\n".join(files.get(filename, []))
                        sync_msg = create_message(FILE_SYNC, filename, body=content)
                        client_sock.sendall(sync_msg.encode())

                    elif command == FILE_UPDATE:
                        filename, line_num_str = args
                        line_num = int(line_num_str)
                        
                        # Dosya yoksa oluştur
                        if filename not in files:
                            files[filename] = []
                        
                        # Satır numarasına kadar boş satırlar ekle
                        while len(files[filename]) < line_num:
                            files[filename].append("")
                        
                        # None değerleri boş string ile değiştir
                        body = body if body is not None else ""
                        files[filename][line_num - 1] = body
                        
                        # Güncellenmiş içeriği gönder
                        updated_content = "\n".join(line if line is not None else "" for line in files[filename])
                        sync_msg = create_message(FILE_SYNC, filename, body=updated_content)
                        broadcast_all(sync_msg)

                    elif command == QUIT:
                        break

            except Exception as e:
                print(f"[HATA] {e}")
                break

        if username:
            print(f"[BİLGİ] {username} bağlantıyı kapattı.")
            usernames.discard(username)
            clients.pop(client_sock, None)
            user_list_msg = create_message(USER_LIST, *usernames)
            broadcast_all(user_list_msg)
            
def parse_multiple_messages(raw_data):
    messages = []
    current_message = ""
    lines = raw_data.split('\n')
    
    for line in lines:
        if ':' in line and not line.startswith('FILE_UPDATE:'):  # Yeni mesaj başlangıcı
            if current_message:
                messages.append(current_message)
            current_message = line
        else:
            if current_message:
                current_message += '\n' + line
            else:
                current_message = line
    
    if current_message:
        messages.append(current_message)
    
    return messages

def start_server():
    print(f"[BAŞLATILIYOR] Sunucu {HOST}:{PORT} adresinde dinleniyor...")
    
    threading.Thread(target=background_auto_save, args=(lambda: files,), daemon=True).start()
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()
        while True:
            client_sock, addr = s.accept()
            print(f"[YENİ BAĞLANTI] {addr}")
            threading.Thread(target=handle_client, args=(client_sock,), daemon=True).start()


if __name__ == '__main__':
    start_server()
