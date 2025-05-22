# shared/messages.py

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

# === Mesaj Olusturucu ===
def create_message(command, *args, body=None):
    """
    Protokole uygun şekilde mesaj oluşturur.
    Args:
        command (str): Komut tipi (örn. LOGIN)
        *args (str): Komut argümanları (örn. kullanıcı adı)
        body (str, optional): Varsa içerik (örn. metin satırı)
    Returns:
        str: Gönderilmeye hazır mesaj
    """
    header = f"{command}:{':'.join(args)}"
    if body is not None:
        return f"{header}\n{body}"
    return header

# === Mesaj Ayrıştırıcı ===
def parse_message(raw_message):
    """
    Gelen mesajı başlık ve içerik olarak ayırır.
    Args:
        raw_message (str): Gelen mesaj (satır sonu dahil olabilir)
    Returns:
        tuple: (command, args, body)
    """
    parts = raw_message.strip().split('\n', 1)
    header = parts[0]
    body = parts[1] if len(parts) == 2 else None

    header_parts = header.split(":")
    command = header_parts[0]
    args = header_parts[1:]

    return command, args, body
