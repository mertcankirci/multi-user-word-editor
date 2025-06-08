# server/server_main.py

import asyncio
import websockets
import json
import sys
import os
import threading
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.messages import parse_message, create_message, LOGIN, USER_LIST, FILE_LIST, FILE_CREATE, FILE_JOIN, FILE_UPDATE, FILE_SYNC, QUIT, ERROR
from server.file_manager import background_auto_save

# === Sunucu Ayarları ===
HOST = '127.0.0.1'
PORT = 5000

# Global state
clients = {}  # websocket -> username
usernames = set()
files = {}  # filename -> list of lines

async def broadcast_all(message, exclude_ws=None):
    """
    Tüm bağlı clientlara mesaj gönderir (belirtilen client hariç).
    Bağlantısı kopan clientları temizler.
    """
    disconnected_clients = []
    for ws in clients:
        if ws != exclude_ws:
            try:
                await ws.send(message)
            except websockets.exceptions.ConnectionClosed:
                disconnected_clients.append(ws)
            except Exception as e:
                print(f"[HATA] Broadcast sırasında hata: {e}")
    
    # Bağlantısı kopan clientları temizle
    for ws in disconnected_clients:
        if ws in clients:
            username = clients[ws]
            usernames.discard(username)
            del clients[ws]
    
    # Eğer client listesi değiştiyse, kullanıcı listesini tekrar yayınla
    if disconnected_clients:
        user_list_msg = create_message(USER_LIST, *usernames)
        await broadcast_all(user_list_msg)

async def handle_client(websocket):
    """
    Her bir client bağlantısını yönetir
    """
    username = None
    try:
        async for message in websocket:
            try:
                command, args, body = parse_message(message)
                
                if command == LOGIN:
                    username = args[0]
                    if username in usernames:
                        # Kullanıcı adı zaten kullanımda
                        error_msg = create_message(ERROR, body="Bu kullanıcı adı zaten kullanımda. Lütfen başka bir ad seçin.")
                        await websocket.send(error_msg)
                        continue
                        
                    clients[websocket] = username
                    usernames.add(username)
                    user_list_msg = create_message(USER_LIST, *usernames)
                    await broadcast_all(user_list_msg)
                    print(f"[BİLGİ] {username} bağlandı")

                    # Yeni bağlanan kullanıcıya mevcut dosya listesini gönder
                    if files:
                        file_list_msg = create_message(FILE_LIST, *files.keys())
                        await websocket.send(file_list_msg)

                elif command == FILE_CREATE:
                    filename = args[0]
                    if filename not in files:
                        files[filename] = []
                        print(f"[BİLGİ] {username} yeni dosya oluşturdu: {filename}")
                        # Dosya oluşturulduktan sonra tüm clientlara güncel dosya listesini gönder
                        file_list_msg = create_message(FILE_LIST, *files.keys())
                        await broadcast_all(file_list_msg)
                    else:
                        error_msg = create_message(ERROR, body="Bu dosya adı zaten mevcut. Lütfen başka bir ad seçin.")
                        await websocket.send(error_msg)

                elif command == FILE_JOIN:
                    filename = args[0]
                    if filename in files:
                        content = "\n".join(files[filename])
                        sync_msg = create_message(FILE_SYNC, filename, body=content)
                        await websocket.send(sync_msg)
                        print(f"[BİLGİ] {username} dosyaya katıldı: {filename}")
                    else:
                        error_msg = create_message(ERROR, body="Dosya bulunamadı.")
                        await websocket.send(error_msg)

                elif command == FILE_UPDATE:
                    filename, line_num_str = args
                    line_num = int(line_num_str)
                    
                    if filename not in files:
                        files[filename] = [] # Yeni oluşturulmuş olabilir, veya JOIN olmadan update
                    
                    # Satır numarasına kadar boş satırlar ekle
                    while len(files[filename]) < line_num:
                        files[filename].append("")
                    
                    # None değerleri boş string ile değiştir
                    body = body if body is not None else ""
                    files[filename][line_num - 1] = body
                    
                    # Güncellenmiş içeriği gönder
                    updated_content = "\n".join(line if line is not None else "" for line in files[filename])
                    sync_msg = create_message(FILE_SYNC, filename, body=updated_content)
                    await broadcast_all(sync_msg, exclude_ws=websocket) # Güncelleyen client'a geri gönderme

                    print(f"[BİLGİ] {username} dosyayı güncelledi: {filename} (Satır {line_num})")

                elif command == QUIT:
                    print(f"[BİLGİ] {username} çıkış yaptı.")
                    break

            except json.JSONDecodeError:
                print(f"[HATA] Geçersiz JSON mesajı: {message}")
                error_msg = create_message(ERROR, body="Geçersiz mesaj formatı.")
                await websocket.send(error_msg)
            except Exception as e:
                print(f"[HATA] Mesaj işleme hatası: {e} (Kullanıcı: {username}, Mesaj: {message})")
                error_msg = create_message(ERROR, body=f"Sunucu hatası: {e}")
                await websocket.send(error_msg)

    except websockets.exceptions.ConnectionClosed:
        print(f"[BİLGİ] {username if username else 'Bilinmeyen kullanıcı'} bağlantıyı kapattı.")
    except Exception as e:
        print(f"[HATA] Client bağlantı hatası: {e}")
    finally:
        if username:
            usernames.discard(username)
            if websocket in clients:
                del clients[websocket]
            user_list_msg = create_message(USER_LIST, *usernames)
            await broadcast_all(user_list_msg) # Bağlantı kapandığında kullanıcı listesini güncelle

async def start_websocket_server():
    """
    WebSocket sunucusunu başlatır
    """
    print(f"[BAŞLATILIYOR] Sunucu {HOST}:{PORT} adresinde dinleniyor...")
    
    # Otomatik kaydetme işlemini ayrı bir thread'de başlat
    # files objesi threading lock ile korunmalı, bu yüzden direkt lambda ile geçmek yerine
    # file_manager'daki lock mekanizmasına güveniyoruz.
    threading.Thread(target=background_auto_save, args=(lambda: files,), daemon=True).start()
    
    async with websockets.serve(handle_client, HOST, PORT):
        await asyncio.Future()  # Sunucuyu çalışır durumda tut

if __name__ == '__main__':
    asyncio.run(start_websocket_server())
