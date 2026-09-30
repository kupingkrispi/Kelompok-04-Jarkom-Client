import argparse
import socket
import sys

from common.protocol import (
    MessageReader, Service, Status, Verdict, Event, MessageType,
    build_request, build_ack, send_message, new_message_id,
)
from common.text_ops import count_characters, count_words, reverse_string, remove_vowels
from common.matrix_ops import determinant_3x3, inverse_3x3, matrices_almost_equal

MENU_ITEMS = [
    ("1", Service.COUNT_CHAR, "Hitung Jumlah Karakter"),
    ("2", Service.COUNT_WORD, "Hitung Jumlah Kata"),
    ("3", Service.REVERSE_STRING, "Balikkan String"),
    ("4", Service.REMOVE_VOWELS, "Hapus Huruf Vokal"),
    ("5", Service.MATRIX_OPS, "Hitung Determinan & Invers Matriks (3x3)"),
]
LABEL_BY_SERVICE = {s: label for _, s, label in MENU_ITEMS}

class Client:
    def __init__(self, host="127.0.0.1", port=5000):
        self.host = host
        self.port = port
        self.enabled_services = set(Service.ALL)
        self.sock = None
        self.reader = None
        self.pending = {}
        self.stopped = False

    def log(self, msg):
        print(msg, flush=True)

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
            return {"determinant": det, "inverse": inv, "invertible": inv is not None}
        raise ValueError(f"Layanan tidak dikenal: {service}")

    def results_match(self, service, expected, received):
        if service == Service.MATRIX_OPS:
            if abs(expected["determinant"] - received["determinant"]) > 1e-4:
                return False
            return matrices_almost_equal(expected["inverse"], received["inverse"])
        return expected == received

    def print_menu(self):
        print("\n=== APLIKASI CLIENT JARINGAN ===")
        for key, _, label in MENU_ITEMS:
            print(f"{key}. {label}")
        print("0. Keluar")

    def read_choice(self):
        valid_keys = [k for k, _, _ in MENU_ITEMS] + ["0"]
        while True:
            choice = input(f"Pilih layanan (0-{len(MENU_ITEMS)}): ").strip()
            if choice in valid_keys:
                return choice
            print("Pilihan tidak valid, coba lagi.")

    def read_text_input(self):
        return input("Masukkan string/teks: ")

    def read_matrix_input(self):
        while True:
            raw = input("Masukkan 9 elemen matriks 3x3 (pisahkan spasi): ").strip()
            parts = raw.split()
            if len(parts) != 9:
                print("Harus tepat 9 angka, coba lagi.")
                continue
            try:
                nums = [float(p) if "." in p else int(p) for p in parts]
            except ValueError:
                print("Semua elemen harus berupa angka, coba lagi.")
                continue
            return [nums[0:3], nums[3:6], nums[6:9]]

    def do_request(self, service):
        if service not in self.enabled_services:
            print(f"Layanan {service} tidak aktif")
            return

        if service == Service.MATRIX_OPS:
            payload = {"matrix": self.read_matrix_input()}
        else:
            payload = {"text": self.read_text_input()}

        expected = self.compute_expected(service, payload)

        msg_id = new_message_id()
        req = build_request(msg_id, service, payload)
        self.pending[msg_id] = (service, payload, expected)
        send_message(self.sock, req)

        while True:
            msg = self.reader.read_message()
            if msg is None:
                print("Koneksi ke server terputus.")
                self.stopped = True
                return
            if msg["type"] == MessageType.RESPONSE:
                self.handle_response(msg)
                break
            elif msg["type"] == MessageType.NOTIFY:
                self.handle_notify(msg)
                if self.stopped:
                    return
            else:
                print(f"Pesan tidak dikenal: {msg}")

        self._drain_pending_notify()

    def _drain_pending_notify(self):
        self.sock.settimeout(0.3)
        try:
            while True:
                msg = self.reader.read_message()
                if msg is None:
                    self.stopped = True
                    return
                if msg["type"] == MessageType.NOTIFY:
                    self.handle_notify(msg)
                else:
                    break
        except socket.timeout:
            pass
        finally:
            self.sock.settimeout(None)

    def handle_response(self, msg):
        msg_id = msg["id"]
        service = msg["service"]
        status = msg["status"]

        info = self.pending.pop(msg_id, None)

        if status == Status.SERVICE_DISABLED:
            print(f"Layanan {service} tidak aktif")
            self.enabled_services.discard(service)
            return

        if status == Status.ERROR:
            print(f"Server error: {msg.get('note')}")
            return

        if info is None:
            return

        _, _, expected = info
        received = msg["result"]
        correct = self.results_match(service, expected, received)
        verdict = Verdict.CORRECT if correct else Verdict.INCORRECT
        tag = "VALID" if correct else "INVALID"

        if service == Service.MATRIX_OPS:
            print(f"hasil determinan ({tag}): {received['determinant']}")
            print(f"hasil invers matriks ({tag}):")
            for row in (received["inverse"] or []):
                print("  " + " ".join(f"{v:.6f}" for v in row))
            if not correct:
                print(f"hasil determinan asli: {expected['determinant']}")
                print("hasil invers matriks asli:")
                for row in (expected["inverse"] or []):
                    print("  " + " ".join(f"{v:.6f}" for v in row))
        else:
            label = LABEL_BY_SERVICE[service].lower()
            print(f"{label} ({tag}): {received}")
            if not correct:
                print(f"hasil asli: {expected}")

        ack = build_ack(msg_id, service, verdict,
                         note=None if correct else f"Diharapkan: {expected}")
        send_message(self.sock, ack)

    def handle_notify(self, msg):
        event = msg["event"]
        if event == Event.WELCOME:
            print(msg["message"])
        elif event == Event.SERVICE_DISABLED:
            self.enabled_services.discard(msg["service"])
        elif event == Event.SERVER_SHUTDOWN:
            print(msg["message"])
            self.stopped = True

    def run(self):
        self.connect()

        while not self.stopped:
            self.print_menu()
            choice = self.read_choice()

            if choice == "0":
                print("Keluar dari aplikasi.")
                break

            service = next(s for k, s, _ in MENU_ITEMS if k == choice)
            self.do_request(service)

            if self.stopped:
                break

        try:
            self.sock.close()
        except OSError:
            pass


def main():
    parser = argparse.ArgumentParser(description="Client interaktif Text & Matrix Service")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()

    client = Client(host=args.host, port=args.port)
    try:
        client.run()
    except KeyboardInterrupt:
        print("\nDihentikan oleh pengguna.")
        sys.exit(0)
    except EOFError:
        print("\nInput berakhir, menutup client.")
        sys.exit(0)


if __name__ == "__main__":
    main()
