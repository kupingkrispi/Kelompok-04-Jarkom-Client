"""
text_ops.py
Berkas ini berisi kumpulan perintah untuk memproses teks atau kalimat. 
Perintah ini digunakan secara bersamaan oleh Server (untuk mencari jawaban) 
dan Client (untuk memeriksa kebenaran jawaban dari Server secara mandiri).
"""

VOWELS = set("aiueoAIUEO")


def count_characters(text: str) -> int:
    """Menghitung jumlah seluruh huruf, angka, tanda baca, hingga spasi di dalam sebuah teks."""
    return len(text)


def count_words(text: str) -> int:
    """Menghitung jumlah kata di dalam sebuah teks yang dipisahkan oleh spasi."""
    return len(text.split())


def reverse_string(text: str) -> str:
    """Membalikkan urutan huruf di dalam sebuah teks dari belakang ke depan."""
    return text[::-1]


def remove_vowels(text: str) -> str:
    """Menghilangkan seluruh huruf vokal (a, i, u, e, o), baik huruf besar maupun kecil, dari sebuah teks."""
    return "".join(ch for ch in text if ch not in VOWELS)
