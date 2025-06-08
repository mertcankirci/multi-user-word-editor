# client/gui.py

import tkinter as tk
from tkinter import simpledialog, messagebox
import asyncio
import websockets
import json
import sys 
import os 
import time
from typing import Optional, Dict, List
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.messages import create_message, parse_message, FILE_LIST, FILE_SYNC, USER_LIST, ERROR, LOGIN, FILE_CREATE, FILE_JOIN, FILE_UPDATE, FILE_SYNC, QUIT

# === İstemci Ayarları ===
HOST = '127.0.0.1'
PORT = 5000

class TextEditorClient:
    def __init__(self, master):
        self.master = master
        self.master.title("Çok Kullanıcılı Metin Editörü")
        
        # WebSocket bağlantısı
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.connected = False
        
        # Kullanıcı bilgileri
        self.username = simpledialog.askstring("Kullanıcı Adı", "Lütfen kullanıcı adınızı girin:")
        if not self.username:
            self.master.destroy()
            return
            
        self.current_file = None
        self.last_update = 0
        self.current_content = [] # Client tarafında da dosya içeriğini takip edelim

        # GUI bileşenlerini oluştur
        self._create_gui()
        
        # Sunucuya bağlan ve mesaj alma döngüsünü başlat
        asyncio.get_event_loop().create_task(self.connect_and_start_receiving())

        # Pencere kapatıldığında temizlik yap
        self.master.protocol("WM_DELETE_WINDOW", self.quit_app_async_wrapper) # Async fonksiyonu wrapper ile çağır


    def _create_gui(self):
        """GUI bileşenlerini oluşturur"""
        # Sol panel: Kullanıcı listesi
        left_frame = tk.Frame(self.master)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        tk.Label(left_frame, text="Bağlı Kullanıcılar").pack()
        self.user_listbox = tk.Listbox(left_frame, width=20)
        self.user_listbox.pack(fill=tk.Y, expand=True)

        # Sağ panel: Dosya işlemleri ve metin editörü
        right_frame = tk.Frame(self.master)
        right_frame.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH, padx=5, pady=5)

        # Dosya seçimi
        file_frame = tk.Frame(right_frame)
        file_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.file_var = tk.StringVar(self.master, value="Dosya Seçin") # Varsayılan metin
        self.file_dropdown = tk.OptionMenu(file_frame, self.file_var, "Dosya Yok") # İlk seçenek
        self.file_dropdown.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Butonlar
        button_frame = tk.Frame(right_frame)
        button_frame.pack(fill=tk.X, pady=(0, 5))
        
        # !!! BURADAKİ BUTTON KOMUTLARINI GÜNCELLEDİK !!!
        tk.Button(button_frame, text="Dosya Oluştur", command=lambda: asyncio.get_event_loop().create_task(self.create_file())).pack(side=tk.LEFT, padx=2)
        tk.Button(button_frame, text="Dosyayı Aç", command=lambda: asyncio.get_event_loop().create_task(self.join_file())).pack(side=tk.LEFT, padx=2)
        tk.Button(button_frame, text="Kaydet", command=lambda: asyncio.get_event_loop().create_task(self.update_file())).pack(side=tk.LEFT, padx=2)
        tk.Button(button_frame, text="Çıkış", command=lambda: asyncio.get_event_loop().create_task(self.quit_app())).pack(side=tk.RIGHT, padx=2)

        # Metin editörü
        self.text_area = tk.Text(right_frame, wrap=tk.WORD)
        self.text_area.pack(expand=True, fill=tk.BOTH)
        
        # Metin değişikliği izleyicisi
        self.text_area.bind('<<Modified>>', self.on_text_modified)
        self.text_area.bind('<KeyRelease>', self.on_text_modified) # Her tuş bırakıldığında kontrol et


    async def connect_and_start_receiving(self):
        """Sunucuya bağlanır ve mesaj alma döngüsünü başlatır."""
        if await self.connect_to_server():
            # Bağlantı başarılıysa, mesaj alma döngüsünü başlat
            await self.receive_messages()

    async def connect_to_server(self):
        """Sunucuya WebSocket bağlantısı kurar"""
        try:
            self.websocket = await websockets.connect(f'ws://{HOST}:{PORT}')
            self.connected = True
            
            # Giriş mesajını gönder
            login_msg = create_message(LOGIN, self.username)
            await self.websocket.send(login_msg)
            
            print(f"[BAĞLANTI] Sunucuya bağlandı: {self.username}")
            return True
        except Exception as e:
            messagebox.showerror("Bağlantı Hatası", str(e))
            self.master.destroy()
            return False

    async def receive_messages(self):
        """Sunucudan gelen mesajları işler"""
        while self.connected:
            try:
                message = await self.websocket.recv()
                command, args, body = parse_message(message)

                if command == FILE_LIST:
                    self.master.after(0, self.update_file_list, args)

                elif command == FILE_SYNC:
                    self.current_file = args[0]
                    self.current_content = body.splitlines() if body else []
                    self.master.after(0, self.update_text_area, body)

                elif command == USER_LIST:
                    self.master.after(0, self.update_user_list, args)

                elif command == ERROR:
                    self.master.after(0, messagebox.showerror, "Hata", body)
                else:
                    print(f"[GELEN MESAJ] {command} {args} {body}")


            except websockets.exceptions.ConnectionClosed:
                self.connected = False
                self.master.after(0, messagebox.showerror, "Bağlantı Hatası", "Sunucu bağlantısı koptu!")
                self.master.after(0, self.master.destroy)
                break
            except json.JSONDecodeError:
                print(f"[HATA] Geçersiz JSON mesajı alındı: {message}")
                # Sunucuya hata göndermeye gerek yok, bu client'ın kendi hatası
            except Exception as e:
                print(f"[HATA] Mesaj alınırken hata: {e}")
                break

    def update_file_list(self, files: List[str]):
        """Dosya listesini günceller"""
        self.file_dropdown['menu'].delete(0, 'end')
        if not files: # Eğer dosya yoksa varsayılan metni göster
            self.file_var.set("Dosya Yok")
            self.file_dropdown['menu'].add_command(label="Dosya Yok", command=None)
        else:
            for fname in files:
                self.file_dropdown['menu'].add_command(
                    label=fname,
                    command=lambda f=fname: self.file_var.set(f)
                )
            # Eğer mevcut dosya seçiliyse onu koru, yoksa ilk dosyayı seç
            if self.current_file and self.current_file in files:
                self.file_var.set(self.current_file)
            elif files and self.file_var.get() == "Dosya Yok": # Sadece ilk başta boşsa otomatik seç
                self.file_var.set(files[0])


    def update_user_list(self, users: List[str]):
        """Kullanıcı listesini günceller"""
        self.user_listbox.delete(0, tk.END)
        for user in users:
            self.user_listbox.insert(tk.END, user)

    def update_text_area(self, content: str):
        """Metin alanını günceller"""
        self.text_area.delete(1.0, tk.END)
        if content:
            self.text_area.insert(tk.END, content)
        self.current_content = content.splitlines() if content else []
        self.text_area.edit_modified(False) # Değişiklik bayrağını temizle


    def on_text_modified(self, event=None):
        """Metin değişikliğini izler ve güncellemeyi tetikler."""
        if not self.current_file or not self.connected:
            return

        # Çok sık güncelleme yapmamak için 0.5 saniye bekle
        current_time = time.time()
        if current_time - self.last_update < 0.5:
            self.text_area.edit_modified(False) # Reset modified flag
            return

        self.last_update = current_time
        # Asenkron update_content'i ayrı bir görev olarak başlat
        asyncio.get_event_loop().create_task(self.update_content())
        self.text_area.edit_modified(False) # Reset modified flag after scheduling update


    async def update_content(self):
        """Metin alanındaki içeriği sunucuya gönderir."""
        if not self.current_file or not self.connected:
            return

        # Get current content from text area
        current_text_area_content = self.text_area.get(1.0, tk.END).strip()
        new_lines = current_text_area_content.splitlines()

        # Check if content has actually changed from what we last know
        if new_lines == self.current_content:
            return # No actual change, skip sending

        # Server'a her satırı tek tek gönder
        # Bu, mevcut protokol yapımıza uygun.
        for i, line in enumerate(new_lines, 1):
            msg = create_message(FILE_UPDATE, self.current_file, str(i), body=line)
            if not await self.send_message(msg):
                return
        
        # Eğer yeni içerik eski içerikten kısaysa, fazla satırları silmek için sunucuya
        # ek bir bilgi göndermemiz gerekebilir. Mevcut protokol bunu desteklemiyor.
        # Ancak, server'dan gelen FILE_SYNC mesajı tam içeriği yeniden senkronize ettiği için
        # bu durum genellikle çözülür.

        # update_content gönderdikten sonra kendi current_content'imizi güncelleyelim
        self.current_content = new_lines


    async def send_message(self, msg: str) -> bool:
        """Güvenli mesaj gönderme fonksiyonu"""
        if not self.connected or not self.websocket:
            return False
        try:
            await self.websocket.send(msg)
            return True
        except websockets.exceptions.ConnectionClosed:
            self.connected = False
            self.master.after(0, messagebox.showerror, "Bağlantı Hatası", "Sunucu bağlantısı koptu!")
            self.master.after(0, self.master.destroy)
            return False
        except Exception as e:
            print(f"[HATA] Mesaj gönderilirken hata: {e}")
            return False

    async def create_file(self):
        """Yeni dosya oluşturur"""
        fname = simpledialog.askstring("Dosya Oluştur", "Yeni dosya adı:")
        if fname and self.connected:
            # Dosya adında boşluk varsa hata verebilir, basit bir kontrol ekleyebiliriz
            if ' ' in fname or ':' in fname or '\\' in fname or '/' in fname:
                messagebox.showerror("Geçersiz Dosya Adı", "Dosya adı boşluk veya özel karakterler içeremez.")
                return

            msg = create_message(FILE_CREATE, fname)
            if not await self.send_message(msg):
                return
            # Dosya oluşturulduktan sonra otomatik olarak bu dosyaya katıl
            self.current_file = fname
            join_msg = create_message(FILE_JOIN, fname)
            await self.send_message(join_msg)


    async def join_file(self):
        """Dosyaya katılır"""
        fname = self.file_var.get()
        if fname and fname != "Dosya Seçin" and fname != "Dosya Yok" and self.connected:
            self.current_file = fname
            msg = create_message(FILE_JOIN, fname)
            await self.send_message(msg)
        else:
            messagebox.showwarning("Uyarı", "Lütfen açmak için geçerli bir dosya seçin.")


    async def update_file(self):
        """Manuel olarak dosya güncellemeyi tetikler."""
        if not self.current_file or not self.connected:
            messagebox.showwarning("Uyarı", "Önce bir dosya açmalısınız.")
            return

        await self.update_content() # update_content'i direkt çağır


    async def quit_app(self):
        """Uygulamadan çıkar"""
        if self.connected and self.websocket:
            try:
                quit_msg = create_message(QUIT, self.username)
                await self.websocket.send(quit_msg)
            except:
                pass # Already closing or connection broken, no need to error
            finally:
                if self.websocket: # Ensure websocket object exists before closing
                    await self.websocket.close()
        self.master.destroy()

    def quit_app_async_wrapper(self):
        """Tkinter protokol handler için asenkron quit_app sarmalayıcısı"""
        asyncio.get_event_loop().create_task(self.quit_app())

def main():
    root = tk.Tk()
    app = TextEditorClient(root)
    
    # Tkinter event loop'unu asyncio ile entegre et
    async def run_tkinter_loop():
        while True:
            root.update_idletasks() # Tkinter'ın bekleyen görevlerini işle
            root.update()          # Tkinter widgetlarını güncelle
            await asyncio.sleep(0.01) # CPU'yu serbest bırakmak için küçük bir gecikme

    try:
        asyncio.get_event_loop().run_until_complete(run_tkinter_loop())
    except tk.TclError: # Pencere kapatıldığında oluşabilir
        pass
    except RuntimeError as e:
        if "cannot run the event loop while another loop is running" in str(e):
            print("[HATA] Zaten çalışan bir event döngüsü var. Uygulama kapatılıyor.")
        else:
            raise


if __name__ == '__main__':
    main()