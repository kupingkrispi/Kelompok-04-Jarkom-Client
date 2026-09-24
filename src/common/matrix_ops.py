"""
matrix_ops.py
Berkas ini berisi rumus perhitungan matematika untuk matriks berukuran 3x3.
Rumus ini digunakan oleh Server dan Client.
"""

from typing import List, Optional

# Pengganti untuk menyederhanakan penulisan struktur data matriks
Matrix = List[List[float]]


def determinant_3x3(m: Matrix) -> float:
    """Menghitung nilai penentu (determinan) dari sebuah matriks 3x3."""
    a, b, c = m[0]
    d, e, f = m[1]
    g, h, i = m[2]
    return a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)


def inverse_3x3(m: Matrix, tol: float = 1e-9) -> Optional[Matrix]:
    """
    Menghitung nilai kebalikan (invers) dari matriks 3x3.
    Akan menghasilkan nilai kosong (None) jika matriks tersebut tidak memiliki nilai kebalikan.
    """
    det = determinant_3x3(m)
    if abs(det) < tol:
        return None

    a, b, c = m[0]
    d, e, f = m[1]
    g, h, i = m[2]

    cofactor = [
        [(e * i - f * h), -(d * i - f * g), (d * h - e * g)],
        [-(b * i - c * h), (a * i - c * g), -(a * h - b * g)],
        [(b * f - c * e), -(a * f - c * d), (a * e - b * d)],
    ]

    # Memutar posisi baris menjadi kolom (transpose) pada perhitungan kofaktor
    adjoint = [[cofactor[col][row] for col in range(3)] for row in range(3)]

    inverse = [[round(adjoint[r][c] / det, 6) for c in range(3)] for r in range(3)]
    return inverse


def matrices_almost_equal(m1: Optional[Matrix], m2: Optional[Matrix], tol: float = 1e-4) -> bool:
    """
    Membandingkan dua buah matriks untuk memastikan apakah nilainya sama.
    Diberikan sedikit batas toleransi karena sistem komputer seringkali 
    memiliki selisih yang sangat kecil saat menghitung angka desimal.
    """
    if m1 is None or m2 is None:
        return m1 == m2
        
    for r in range(len(m1)):
        for c in range(len(m1[0])):
            if abs(m1[r][c] - m2[r][c]) > tol:
                return False
                
    return True
