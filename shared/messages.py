# shared/messages.py

import json
from typing import List, Tuple, Optional, Dict, Any

# === Mesaj Tipi Sabitleri ===
LOGIN = "LOGIN"
USER_LIST = "USER_LIST"
FILE_CREATE = "FILE_CREATE"
FILE_LIST = "FILE_LIST"
FILE_JOIN = "FILE_JOIN"
FILE_UPDATE = "FILE_UPDATE"
FILE_SYNC = "FILE_SYNC"
FILE_SAVE = "FILE_SAVE"
QUIT = "QUIT"
ERROR = "ERROR"  # Yeni: Hata mesajları için

# === Mesaj Olusturucu ===
def create_message(command: str, *args: str, body: Optional[str] = None) -> str:
    """
    Protokole uygun şekilde mesaj oluşturur.
    Args:
        command (str): Komut tipi (örn. LOGIN)
        *args (str): Komut argümanları (örn. kullanıcı adı)
        body (str, optional): Varsa içerik (örn. metin satırı)
    Returns:
        str: JSON formatında mesaj
    """
    message = {
        "command": command,
        "args": list(args),
        "body": body
    }
    return json.dumps(message)

# === Mesaj Ayrıştırıcı ===
def parse_message(raw_message: str) -> Tuple[str, List[str], Optional[str]]:
    """
    Gelen mesajı başlık ve içerik olarak ayırır.
    Args:
        raw_message (str): JSON formatında gelen mesaj
    Returns:
        tuple: (command, args, body)
    """
    try:
        message = json.loads(raw_message)
        return (
            message.get("command", ""),
            message.get("args", []),
            message.get("body")
        )
    except json.JSONDecodeError:
        # Eski format mesajları için geriye dönük uyumluluk
        parts = raw_message.strip().split('\n', 1)
        header = parts[0]
        body = parts[1] if len(parts) == 2 else None

        header_parts = header.split(":")
        command = header_parts[0]
        args = header_parts[1:]

        return command, args, body

# === Yardımcı Fonksiyonlar ===
def create_error_message(error_text: str) -> str:
    """
    Hata mesajı oluşturur.
    Args:
        error_text (str): Hata mesajı
    Returns:
        str: JSON formatında hata mesajı
    """
    return create_message(ERROR, body=error_text)

def is_error_message(message: str) -> bool:
    """
    Mesajın hata mesajı olup olmadığını kontrol eder.
    Args:
        message (str): Kontrol edilecek mesaj
    Returns:
        bool: Hata mesajı ise True
    """
    try:
        parsed = json.loads(message)
        return parsed.get("command") == ERROR
    except json.JSONDecodeError:
        return False

def format_file_content(content: List[str]) -> str:
    """
    Dosya içeriğini formatlar.
    Args:
        content (List[str]): Dosya satırları
    Returns:
        str: Formatlanmış içerik
    """
    return "\n".join(line if line is not None else "" for line in content)

def parse_file_content(content: str) -> List[str]:
    """
    Formatlanmış içeriği dosya satırlarına dönüştürür.
    Args:
        content (str): Formatlanmış içerik
    Returns:
        List[str]: Dosya satırları
    """
    return content.splitlines() if content else []
