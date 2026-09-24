# Rancangan Protokol — Text & Matrix Service

## 1. Gambaran Umum

Protokol ini berjalan di atas **TCP** (connection-oriented, reliable, byte-stream).
Satu koneksi TCP dipakai untuk seluruh sesi antara satu client dan server.

Setiap **pesan** dikodekan sebagai satu objek **JSON** dalam satu baris teks,
diakhiri karakter newline (`\n`) sebagai delimiter — format ini disebut
*line-delimited JSON (NDJSON)*. Delimiter diperlukan karena TCP adalah aliran
byte tanpa batas pesan (tidak seperti UDP yang berbasis datagram) sehingga
pengirim dan penerima harus sepakat kapan satu pesan logis berakhir.

```
<json-object-1>\n<json-object-2>\n<json-object-3>\n ...
```

## 2. Jenis Pesan (Message Type)

| Jenis      | Arah              | Fungsi                                                        |
|------------|-------------------|----------------------------------------------------------------|
| `REQUEST`  | Client → Server   | Meminta server menjalankan salah satu layanan                 |
| `RESPONSE` | Server → Client   | Mengirim hasil (atau status gagal) dari `REQUEST` terkait      |
| `ACK`      | Client → Server   | Menyatakan apakah `RESPONSE` yang diterima **benar/salah**     |
| `NOTIFY`   | Server → Client   | Notifikasi asinkron: sambutan, layanan nonaktif, server berhenti |

## 3. Sintaksis dan Semantik Pesan

### 3.1 REQUEST (Client → Server)
```json
{
  "type": "REQUEST",
  "id": 7,
  "service": "COUNT_CHAR",
  "payload": { "text": "contoh string" }
}
```
- `id` (int): identitas unik pesan, dibuat oleh client, digunakan untuk
  mengaitkan `RESPONSE` dan `ACK` dengan `REQUEST` ini.
- `service` (string): salah satu dari lima layanan:
  `COUNT_CHAR`, `COUNT_WORD`, `REVERSE_STRING`, `REMOVE_VOWELS`, `MATRIX_OPS`.
- `payload` (object): data masukan, tergantung layanan:
  - `COUNT_CHAR`, `COUNT_WORD`, `REVERSE_STRING`, `REMOVE_VOWELS` →
    `{"text": "<string>"}`
  - `MATRIX_OPS` → `{"matrix": [[a,b,c],[d,e,f],[g,h,i]]}` (matriks 3×3)

### 3.2 RESPONSE (Server → Client)
```json
{
  "type": "RESPONSE",
  "id": 7,
  "service": "COUNT_CHAR",
  "status": "OK",
  "result": 13,
  "note": null
}
```
- `id`: **sama** dengan `id` pada `REQUEST` yang dijawab.
- `status` (string):
  - `OK` — layanan berhasil dijalankan, `result` berisi jawaban
    (bisa jadi **sengaja dibuat salah**, lihat §5).
  - `SERVICE_DISABLED` — layanan yang diminta sudah dinonaktifkan;
    `result` bernilai `null`.
  - `ERROR` — permintaan tidak valid (ex. payload tidak sesuai format).
- `result` — bentuknya tergantung layanan:
  - `COUNT_CHAR`, `COUNT_WORD` → integer
  - `REVERSE_STRING`, `REMOVE_VOWELS` → string
  - `MATRIX_OPS` → `{"determinant": float, "inverse": [[..]] | null, "invertible": bool}`
    (`inverse` bernilai `null` jika matriks singular, yaitu determinan ≈ 0)

### 3.3 ACK (Client → Server)
```json
{
  "type": "ACK",
  "id": 7,
  "service": "COUNT_CHAR",
  "verdict": "CORRECT",
  "note": null
}
```
- `id`: id `RESPONSE` yang sedang diverifikasi.
- `verdict`: `CORRECT` jika hasil server cocok dengan hasil hitungan
  independen client, atau `INCORRECT` jika tidak cocok.
- `note`: opsional, berisi nilai yang seharusnya benar (untuk keperluan log/debug).

### 3.4 NOTIFY (Server → Client)
```json
{
  "type": "NOTIFY",
  "id": 42,
  "event": "SERVICE_DISABLED",
  "service": "REVERSE_STRING",
  "message": "Layanan REVERSE_STRING dinonaktifkan karena mengirim jawaban salah."
}
```
- `event`:
  - `WELCOME` — dikirim sekali saat client baru terhubung, berisi daftar layanan aktif.
  - `SERVICE_DISABLED` — satu layanan baru saja dinonaktifkan, `service` diisi nama layanannya.
  - `SERVER_SHUTDOWN` — seluruh layanan sudah nonaktif, server akan menutup semua koneksi dan berhenti.

## 4. Diagram Pertukaran Pesan (Sequence)

```
Client                                   Server
  |                                         |
  |  <-------------- NOTIFY(WELCOME) ------ |   (saat koneksi dibuka)
  |                                         |
  |----- REQUEST(service, payload) ------->|
  |                                         | hitung jawaban benar
  |                                         | (± acak: kirim yang salah)
  |<---- RESPONSE(status, result) ----------|
  | verifikasi lokal (hitung sendiri)       |
  |----- ACK(verdict) -------------------->|
  |                                         | jika verdict=INCORRECT:
  |                                         |   nonaktifkan service tsb
  |<---- NOTIFY(SERVICE_DISABLED) ----------|   (broadcast ke semua client)
  |                                         |
  |  ... berulang untuk layanan lain ...    |
  |                                         |
  |                                         | jika SEMUA layanan nonaktif:
  |<---- NOTIFY(SERVER_SHUTDOWN) -----------|
  |  (client berhenti mengirim request)     |  (server tutup semua koneksi & exit)
```

## 5. Aturan Protokol (Rules)

1. **R1 — Hubungan pesan:** setiap `REQUEST` dijawab tepat satu `RESPONSE`
   dengan `id` yang sama. Client mengaitkan `ACK` ke `id` `RESPONSE` yang sama pula.
2. **R2 — ACK hanya untuk status OK:** client hanya mengirim `ACK` setelah
   menerima `RESPONSE` dengan `status = OK`. `RESPONSE` dengan status
   `SERVICE_DISABLED` atau `ERROR` tidak perlu di-ACK.
3. **R3 — Jawaban server bisa sengaja salah:** server secara acak mengirim hasil yang
   keliru untuk menguji ketelitian client dalam memverifikasi.
4. **R4 — Verifikasi independen di client:** client **wajib** menghitung
   sendiri jawaban yang seharusnya benar (bukan hanya mempercayai server)
   sebelum menentukan `verdict` pada `ACK`.
5. **R5 — Efek dari verdict INCORRECT:** begitu server menerima `ACK` dengan
   `verdict = INCORRECT`, server **menonaktifkan** layanan terkait secara
   global (berlaku untuk semua client), namun layanan lain yang masih
   memberi jawaban benar **tetap berjalan**.
6. **R6 — Notifikasi wajib:** setiap kali sebuah layanan dinonaktifkan,
   server **wajib** mem-broadcast `NOTIFY(SERVICE_DISABLED)` ke semua
   client yang sedang terhubung.
7. **R7 — Permintaan ke layanan nonaktif:** jika client (ex. karena race
   condition atau belum menerima notifikasi terbaru) mengirim `REQUEST`
   untuk layanan yang sudah nonaktif, server membalas `RESPONSE` dengan
   `status = SERVICE_DISABLED`, bukan mengabaikan permintaan.
8. **R8 — Penghentian server:** ketika **seluruh** layanan berstatus
   nonaktif, server mem-broadcast `NOTIFY(SERVER_SHUTDOWN)` ke semua
   client, lalu menutup semua koneksi dan menghentikan proses.
9. **R9 — Penghentian client:** setelah menerima `NOTIFY(SERVER_SHUTDOWN)`,
   client berhenti mengirim `REQUEST` baru dan menutup koneksinya.

## 6. Contoh Kasus MATRIX_OPS

**Request:**
```json
{"type":"REQUEST","id":5,"service":"MATRIX_OPS","payload":{"matrix":[[4,2,-3],[0,5,-5],[-3,-5,3]]}}
```

**Response (benar):**
```json
{
  "type": "RESPONSE", "id": 5, "service": "MATRIX_OPS", "status": "OK",
  "result": {
    "determinant": -55,
    "inverse": [[0.181818,-0.163636,-0.090909],
                [-0.272727,-0.054545,-0.363636],
                [-0.272727,-0.254545,-0.363636]],
    "invertible": true
  },
  "note": null
}
```

**ACK client (jika server mengirim determinan yang salah, mis. -45):**
```json
{"type":"ACK","id":5,"service":"MATRIX_OPS","verdict":"INCORRECT","note":"Diharapkan: -55"}
```
