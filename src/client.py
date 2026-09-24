import argparse
import random
import socket
import sys
import time

from common.protocol import MessageReader, MessageType, Service, build_request, send_message, new_message_id

SAMPLE_SENTENCES = [
    "jaringan komputer itu menyenangkan",
    "protokol adalah aturan komunikasi",
    "socket TCP menjamin pengiriman data",
    "python mudah dipakai untuk prototyping",
    "client server architecture is everywhere",
    "tugas jaringan komputer semester ini",
]

def random_matrix():
    return [[random.randint(0, 5) for _ in range(3)] for _ in range(3)]

def random_payload(service):
    if service == Service.MATRIX_OPS:
        return {"matriks": random_matrix()}
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

    def send_request(self):
        service = random.choice(list(self.enabled_services))
        payload = random_payload(service)
        expected = self.compute_expected(service, payload)

        msg_id = new_message_id()
        req = build_request(msg_id, service, payload)
        self.pending[msg_id] = (service, payload, expected)

        send_message(self.sock, req)
        self.log(f"Mengirim REQUEST id={msg_id} service={service} payload={payload}")

    # TODO (P3): 
    # - Hitung hasil yang diharapkan (expected result) secara lokal di client
    #   berdasarkan parameter `service` dan `payload` yang dikirim.
    def compute_expected(self, service, payload):
        raise NotImplementedError("TODO (Person 3)")

    # TODO (P3): 
    # - Bandingkan hasil komputasi lokal (`expected`) dengan hasil 
    #   yang dikembalikan oleh server (`received`).
    # - Kembalikan True jika cocok, False jika berbeda.
    def results_match(self, service, expected, received):
        raise NotImplementedError("TODO (Person 3)")

    # TODO (P4): 
    # - Ambil data dari `msg` respons server.
    # - Cari request aslinya di `self.pending`.
    # - Panggil `compute_expected` dan `results_match` dari Person 3 untuk validasi.
    # - Cetak log sukses atau gagalnya.
    def handle_response(self, msg):
        raise NotImplementedError("TODO (Person 4)")

    # TODO (P4): 
    # - Tangani jika pesan dari server berupa broadcast/notifikasi.
    # - Tampilkan isi pesan notifikasi tersebut ke layar (log).
    def handle_notify(self, msg):
        raise NotImplementedError("TODO (Person 4)")

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
