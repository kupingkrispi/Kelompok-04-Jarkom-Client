"""
protocol.py
Definisi protokol aplikasi "Text & Matrix Service" via TCP.
Menggunakan format line-delimited JSON (NDJSON) yang dipisahkan oleh newline ("\\n").
Referensi lengkap struktur JSON dan aturan komunikasi terdapat pada protocol.md.
"""

import json
import socket
import itertools
from typing import Any, Dict, List, Optional


class MessageType:
    REQUEST = "REQUEST"
    RESPONSE = "RESPONSE"
    ACK = "ACK"
    NOTIFY = "NOTIFY"


class Service:
    COUNT_CHAR = "COUNT_CHAR"
    COUNT_WORD = "COUNT_WORD"
    REVERSE_STRING = "REVERSE_STRING"
    REMOVE_VOWELS = "REMOVE_VOWELS"
    MATRIX_OPS = "MATRIX_OPS"

    ALL: List[str] = [
        COUNT_CHAR,
        COUNT_WORD,
        REVERSE_STRING,
        REMOVE_VOWELS,
        MATRIX_OPS,
    ]


class Status:
    OK = "OK"
    SERVICE_DISABLED = "SERVICE_DISABLED"
    ERROR = "ERROR"


class Verdict:
    CORRECT = "CORRECT"
    INCORRECT = "INCORRECT"


class Event:
    WELCOME = "WELCOME"
    SERVICE_DISABLED = "SERVICE_DISABLED"
    SERVER_SHUTDOWN = "SERVER_SHUTDOWN"


_id_counter = itertools.count(1)


def new_message_id() -> int:
    """Menghasilkan id pesan unik per proses."""
    return next(_id_counter)


# ------------------------------------------------------------------
# Builder Pesan
# ------------------------------------------------------------------

def build_request(msg_id: int, service: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Membuat pesan REQUEST (Client -> Server)."""
    return {
        "type": MessageType.REQUEST,
        "id": msg_id,
        "service": service,
        "payload": payload,
    }


def build_response(
    msg_id: int, service: str, status: str, result: Any = None, note: Optional[str] = None
) -> Dict[str, Any]:
    """Membuat pesan RESPONSE (Server -> Client)."""
    return {
        "type": MessageType.RESPONSE,
        "id": msg_id,
        "service": service,
        "status": status,
        "result": result,
        "note": note,
    }


def build_ack(
    msg_id: int, service: str, verdict: str, note: Optional[str] = None
) -> Dict[str, Any]:
    """Membuat pesan ACK untuk verifikasi hasil (Client -> Server)."""
    return {
        "type": MessageType.ACK,
        "id": msg_id,
        "service": service,
        "verdict": verdict,
        "note": note,
    }


def build_notify(
    event: str, message: str, service: Optional[str] = None
) -> Dict[str, Any]:
    """Membuat pesan NOTIFY asinkron (Server -> Client)."""
    return {
        "type": MessageType.NOTIFY,
        "id": new_message_id(),
        "event": event,
        "service": service,
        "message": message,
    }


# ------------------------------------------------------------------
# Komunikasi Jaringan (TCP NDJSON)
# ------------------------------------------------------------------
ENCODING = "utf-8"


def send_message(sock: socket.socket, message: Dict[str, Any]) -> None:
    """Mengirim satu pesan JSON diakhiri newline via TCP."""
    data = (json.dumps(message) + "\n").encode(ENCODING)
    sock.sendall(data)


class MessageReader:
    """
    Buffer socket TCP untuk membaca pesan JSON baris per baris.
    Menangani isu fragmentasi dan coalescing pada aliran TCP.
    """

    def __init__(self, sock: socket.socket):
        self.sock = sock
        self._buffer = b""

    def read_message(self) -> Optional[Dict[str, Any]]:
        """Mengembalikan dict pesan berikutnya, atau None jika koneksi ditutup."""
        while b"\n" not in self._buffer:
            chunk = self.sock.recv(4096)
            if not chunk:
                return None
            self._buffer += chunk
            
        line, _, self._buffer = self._buffer.partition(b"\n")
        
        if not line.strip():
            return self.read_message()
            
        return json.loads(line.decode(ENCODING))
