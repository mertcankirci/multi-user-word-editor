# client/client_main.py

import asyncio
import websockets
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.messages import parse_message, create_message, USER_LIST, FILE_LIST, FILE_SYNC

# === İstemci Ayarları ===
HOST = '127.0.0.1'
PORT = 5000

class CLIEditor:
    def __init__(self):
        self.websocket = None
        self.connected = False
        self.username = None
        self.current_file = None
        self.current_content = []

    async def connect_to_server(self):
        """Sunucuya WebSocket bağlantısı kurar"""
        try:
            self.websocket = await websockets.connect(f'ws://{HOST}:{PORT}')
            self.connected = True
            print("[BAĞLANTI] Sunucuya bağlandı")
            return True
        except Exception as e:
            print(f"[HATA] Bağlantı hatası: {e}")
            return False

    async def receive_messages(self):
        """Sunucudan gelen mesajları işler"""
        while self.connected:
            try:
                message = await self.websocket.recv()
                command, args, body = parse_message(message)

                if command == USER_LIST:
                    print("\n[Bağlı Kullanıcılar]", ', '.join(args))

                elif command == FILE_LIST:
                    print("\n[Mevcut Dosyalar]", ', '.join(args))

                elif command == FILE_SYNC:
                    filename = args[0]
                    self.current_file = filename
                    self.current_content = body.splitlines() if body else []
                    print(f"\n[{filename} Güncellendi]")
                    self.display_current_file()

                elif command == "ERROR":
                    print(f"\n[HATA] {body}")

            except websockets.exceptions.ConnectionClosed:
                print("\n[BAĞLANTI KOPTU] Sunucu bağlantısı kesildi")
                self.connected = False
                break
            except Exception as e:
                print(f"\n[HATA] Mesaj alınırken hata: {e}")
                break

    def display_current_file(self):
        """Mevcut dosyanın içeriğini gösterir"""
        if not self.current_file:
            return

        print(f"\n=== {self.current_file} ===")
        for i, line in enumerate(self.current_content, 1):
            print(f"{i:3d} | {line}")
        print("=" * 30)

    async def send_message(self, msg):
        """Sunucuya mesaj gönderir"""
        if not self.connected:
            return False
        try:
            await self.websocket.send(msg)
            return True
        except:
            self.connected = False
            print("\n[BAĞLANTI KOPTU] Mesaj gönderilemedi")
            return False

    async def handle_user_input(self):
        """Kullanıcı girdilerini işler"""
        while self.connected:
            try:
                print("\nKomutlar: CREATE, JOIN, UPDATE, QUIT")
                cmd = input("Komut girin: ").strip().upper()

                if cmd == "CREATE":
                    filename = input("Dosya adı: ")
                    msg = create_message("FILE_CREATE", filename)
                    await self.send_message(msg)

                elif cmd == "JOIN":
                    filename = input("Düzenlenecek dosya: ")
                    msg = create_message("FILE_JOIN", filename)
                    await self.send_message(msg)

                elif cmd == "UPDATE":
                    if not self.current_file:
                        print("[UYARI] Önce bir dosya açmalısınız (JOIN)")
                        continue

                    try:
                        line_num = int(input("Satır numarası: "))
                        if line_num < 1:
                            raise ValueError
                        
                        content = input("Yeni içerik: ")
                        msg = create_message("FILE_UPDATE", self.current_file, str(line_num), body=content)
                        await self.send_message(msg)
                    except ValueError:
                        print("[HATA] Geçersiz satır numarası")

                elif cmd == "QUIT":
                    msg = create_message("QUIT", self.username)
                    await self.send_message(msg)
                    break

                else:
                    print("[UYARI] Geçersiz komut")

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"[HATA] Komut işlenirken hata: {e}")

    async def run(self):
        """Ana uygulama döngüsü"""
        if not await self.connect_to_server():
            return

        self.username = input("Kullanıcı adınızı girin: ")
        login_msg = create_message("LOGIN", self.username)
        if not await self.send_message(login_msg):
            return

        # Mesaj alma ve kullanıcı girdisi işleme görevlerini başlat
        receive_task = asyncio.create_task(self.receive_messages())
        input_task = asyncio.create_task(self.handle_user_input())

        # Görevlerden biri tamamlanana kadar bekle
        done, pending = await asyncio.wait(
            [receive_task, input_task],
            return_when=asyncio.FIRST_COMPLETED
        )

        # Bekleyen görevleri iptal et
        for task in pending:
            task.cancel()

        # Bağlantıyı kapat
        if self.websocket:
            await self.websocket.close()

def main():
    editor = CLIEditor()
    asyncio.run(editor.run())

if __name__ == '__main__':
    main()