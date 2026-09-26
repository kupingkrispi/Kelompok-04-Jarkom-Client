import argparse
import random
import socket
import sys
import time

from common.protocol import (
    MessageReader, Service, Status, Verdict, Event, MessageType,
    build_request, build_ack, send_message, new_message_id,
)

from common.text_ops import (
    count_characters,
    count_words,
    reverse_string,
    remove_vowels,
)

from common.matrix_ops import determinant_3x3, inverse_3x3

SAMPLE_SENTENCES = [
    "jaringan komputer itu menyenangkan",
    "protokol adalah aturan komunikasi",
    "socket TCP menjamin pengiriman data",
    "python mudah dipakai untuk prototyping",
    "client server architecture is everywhere",
    "tugas jaringan komputer semester ini",
]

def random_matrix():
    return [[random.randint(-5, 5) for _ in range(3)] for _ in range(3)]

def random_payload(service):
    if service == Service.MATRIX_OPS:
        return {"matrix": random_matrix()}
    return {"text": random.choice(SAMPLE_SENTENCES)}

class Client:
    def __init__(self, host="127.0.0.1", port=5000, delay=1.5, max_requests=None):
        self.host = host
        self.port = port
        self.delay = delay
        self.max_requests = max_requests

        self.enabled_services = set(Service.ALL)
        self.sock = None
        self.reader = None
        self.pending = {}
        self.stopped = False

    def log(self, msg):
        ts = time.strftime("%H:%M:%S")
        print(f"[{ts}] [CLIENT] {msg}", flush=True)

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        self.reader = MessageReader(self.sock)
        self.log(f"Terhubung ke server {self.host}:{self.port}")

    def compute_expected(self, service, payload):
        if service == Service.COUNT_CHAR:
            return count_characters(payload["text"])

        if service == Service.COUNT_WORD:
            return count_words(payload["text"])

        if service == Service.REVERSE_STRING:
            return reverse_string(payload["text"])

        if service == Service.REMOVE_VOWELS:
            return remove_vowels(payload["text"])

        if service == Service.MATRIX_OPS:
            m = payload["matrix"]
            det = determinant_3x3(m)
            inv = inverse_3x3(m)

            return {
                "determinant": det,
                "inverse": inv,
                "invertible": inv is not None
            }

        raise ValueError(f"Layanan tidak dikenal: {service}")

    def results_match(self, service, expected, received):
        return expected == received

    def send_request(self):
        service = random.choice(list(self.enabled_services))
        payload = random_payload(service)
        expected = self.compute_expected(service, payload)

        msg_id = new_message_id()
        req = build_request(msg_id, service, payload)
        self.pending[msg_id] = (service, payload, expected)

        send_message(self.sock, req)
        self.log(f"Mengirim REQUEST id={msg_id} service={service} payload={payload}")

    def handle_response(self, msg):
        msg_id = msg["id"]
        service = msg["service"]
        status = msg["status"]

        info = self.pending.pop(msg_id, None)

        if status == Status.SERVICE_DISABLED:
            self.log(f"Server menolak: layanan {service} sudah nonaktif. ({msg.get('note')})")
            self.enabled_services.discard(service)
            return

        if status == Status.ERROR:
            self.log(f"Server error untuk service {service}: {msg.get('note')}")
            return

        if info is None:
            self.log(f"RESPONSE id={msg_id} tidak dikenali, diabaikan")
            return

        _, _, expected = info
        received = msg["result"]

        correct = self.results_match(service, expected, received)
        # verdict sekarang mengikuti fakta: CORRECT jika cocok, INCORRECT jika tidak cocok
        verdict = Verdict.CORRECT if correct else Verdict.INCORRECT

        self.log(
            f"RESPONSE id={msg_id} service={service} "
            f"hasil_server={received} | hasil_hitung_sendiri={expected} => {verdict}"
        )

        ack = build_ack(msg_id, service, verdict,
                         note=None if correct else f"Diharapkan: {expected}")
        send_message(self.sock, ack)
        self.log(f"Mengirim ACK id={msg_id} verdict={verdict}")

    def handle_notify(self, msg):
        event = msg["event"]
        if event == Event.WELCOME:
            self.log(msg["message"])
        elif event == Event.SERVICE_DISABLED:
            service = msg["service"]
            # service yang dinonaktifkan sekarang benar-benar dihapus dari daftar layanan aktif
            self.enabled_services.discard(service)
            self.log(f"NOTIFY: {msg['message']} (sisa layanan aktif: {sorted(self.enabled_services)})")
        elif event == Event.SERVER_SHUTDOWN:
            self.log(f"NOTIFY: {msg['message']}")
            self.stopped = True

    def run(self):
        self.connect()
        request_count = 0
        while not self.stopped:
            if self.max_requests is not None and request_count >= self.max_requests:
                self.log("Batas jumlah request tercapai, client berhenti.")
                break
            if not self.enabled_services:
                self.log("Tidak ada layanan aktif yang diketahui, client berhenti.")
                break

            self.send_request()
            request_count += 1

            got_response = False
            while not got_response and not self.stopped:
                msg = self.reader.read_message()
                if msg is None:
                    self.log("Koneksi ke server terputus.")
                    self.stopped = True
                    break
                    
                if msg["type"] == MessageType.RESPONSE:
                    self.handle_response(msg)
                    got_response = True
                elif msg["type"] == MessageType.NOTIFY:
                    self.handle_notify(msg)
                else:
                    self.log(f"Pesan tidak dikenal: {msg}")

                if not self.stopped:
                    time.sleep(self.delay)
                    
            self.log("Menutup koneksi client.")
            if self.sock:
                self.sock.close()


def main():
    parser = argparse.ArgumentParser(description="Client Text & Matrix Service")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--delay", type=float, default=1.5, help="Jeda antar request (detik)")
    parser.add_argument("--requests", type=int, default=None, help="Batas jumlah request (default: tanpa batas)")
    args = parser.parse_args()

    client = Client(host=args.host, port=args.port, delay=args.delay, max_requests=args.requests)
    
    client.run()
    
if __name__ == "__main__":
    main()
