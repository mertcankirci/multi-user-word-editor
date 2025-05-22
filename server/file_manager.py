# server/file_manager.py

import os
import threading
import time

SAVE_INTERVAL = 10  # saniye
SAVE_DIR = "saved_files"

# filename -> list of lines
documents = {}  # bu aslında server_main'deki files ile senkronize edilmeli
lock = threading.Lock()

def ensure_save_dir():
    if not os.path.exists(SAVE_DIR):
        os.makedirs(SAVE_DIR)

def save_file(filename, lines):
    ensure_save_dir()
    path = os.path.join(SAVE_DIR, filename)
    # None değerleri boş string ile değiştir
    lines = [line if line is not None else "" for line in lines]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def background_auto_save(get_all_documents_func):
    """
    get_all_documents_func: callable that returns {filename: [lines]}
    """
    while True:
        time.sleep(SAVE_INTERVAL)
        try:
            all_docs = get_all_documents_func()
            with lock:
                for fname, lines in all_docs.items():
                    if lines is not None:  # None kontrolü ekle
                        save_file(fname, lines)
            print("[OTOMATİK KAYIT] Tüm dosyalar kaydedildi.")
        except Exception as e:
            print(f"[KAYIT HATASI] {e}")
