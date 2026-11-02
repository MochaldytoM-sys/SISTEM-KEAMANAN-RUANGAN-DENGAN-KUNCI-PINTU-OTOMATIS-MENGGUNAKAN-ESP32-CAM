import os
import time
import smtplib
import requests
import face_recognition
import numpy as np

from io import BytesIO
from datetime import datetime
from email.message import EmailMessage


# ==========================================
# KONFIGURASI ESP32-CAM
# ==========================================

CAMERA_URL = "http://192.168.1.100/capture"

# Ganti dengan IP ESP32-CAM yang sebenarnya.
# Pastikan laptop dan ESP32-CAM terhubung
# ke jaringan Wi-Fi yang sama.


# ==========================================
# KONFIGURASI EMAIL
# ==========================================

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

EMAIL_PENGIRIM = "emailkamu@gmail.com"
EMAIL_PENERIMA = "emailpenerima@gmail.com"

# Gunakan App Password Gmail, bukan password
# utama akun Google.
EMAIL_APP_PASSWORD = "MASUKKAN_APP_PASSWORD"


# ==========================================
# KONFIGURASI PENGENALAN WAJAH
# ==========================================

FOLDER_WAJAH = "known_faces"

# Nilai lebih kecil berarti pencocokan lebih ketat.
BATAS_KEMIRIPAN = 0.48

# Jeda minimum sebelum mengirim peringatan
# berikutnya, dalam detik.
JEDA_EMAIL = 60

# Interval pengambilan gambar.
INTERVAL_CEK = 2


# ==========================================
# MEMUAT DATA WAJAH YANG DIKENALI
# ==========================================

wajah_terdaftar = []
nama_terdaftar = []


def muat_wajah_terdaftar():
    if not os.path.isdir(FOLDER_WAJAH):
        raise FileNotFoundError(
            f"Folder {FOLDER_WAJAH} tidak ditemukan."
        )

    for nama_file in os.listdir(FOLDER_WAJAH):

        if not nama_file.lower().endswith(
            (".jpg", ".jpeg", ".png")
        ):
            continue

        lokasi = os.path.join(
            FOLDER_WAJAH, nama_file
        )

        gambar = face_recognition.load_image_file(
            lokasi
        )

        encoding = face_recognition.face_encodings(
            gambar
        )

        if len(encoding) == 0:
            print(
                f"[PERINGATAN] Wajah tidak ditemukan "
                f"pada {nama_file}"
            )
            continue

        if len(encoding) > 1:
            print(
                f"[PERINGATAN] Ada lebih dari satu wajah "
                f"pada {nama_file}; foto dilewati."
            )
            continue

        nama = os.path.splitext(nama_file)[0]

        wajah_terdaftar.append(encoding[0])
        nama_terdaftar.append(nama)

        print(f"[TERDAFTAR] Wajah: {nama}")

    if len(wajah_terdaftar) == 0:
        raise RuntimeError(
            "Belum ada wajah valid yang terdaftar."
        )


# ==========================================
# MENGIRIM EMAIL PERINGATAN
# ==========================================

def kirim_email_peringatan(gambar_jpeg, jumlah_wajah):

    waktu = datetime.now().strftime(
        "%d-%m-%Y %H:%M:%S"
    )

    pesan = EmailMessage()

    pesan["Subject"] = (
        "[PERINGATAN] Wajah Tidak Dikenali"
    )

    pesan["From"] = EMAIL_PENGIRIM
    pesan["To"] = EMAIL_PENERIMA

    pesan.set_content(
        f"""
Peringatan keamanan Smart Door Lock

Waktu kejadian: {waktu}

Sistem mendeteksi {jumlah_wajah} wajah
yang tidak cocok dengan data wajah terdaftar.

Foto kejadian dilampirkan pada email ini.

Catatan:
Peringatan ini tidak membuktikan bahwa
orang tersebut melakukan tindakan berbahaya.

Sistem RFID tetap menjadi mekanisme akses pintu.
        """.strip()
    )

    pesan.add_attachment(
        gambar_jpeg,
        maintype="image",
        subtype="jpeg",
        filename="wajah_tidak_dikenali.jpg"
    )

    with smtplib.SMTP(
        SMTP_SERVER, SMTP_PORT, timeout=20
    ) as server:

        server.ehlo()
        server.starttls()
        server.ehlo()

        server.login(
            EMAIL_PENGIRIM,
            EMAIL_APP_PASSWORD
        )

        server.send_message(pesan)

    print("[EMAIL] Peringatan berhasil dikirim.")


# ==========================================
# MENGAMBIL GAMBAR DARI ESP32-CAM
# ==========================================

def ambil_gambar_kamera():

    respons = requests.get(
        CAMERA_URL,
        timeout=10
    )

    respons.raise_for_status()

    if not respons.headers.get(
        "Content-Type", ""
    ).startswith("image/"):
        raise ValueError(
            "Respons kamera bukan gambar."
        )

    data_gambar = respons.content

    gambar = face_recognition.load_image_file(
        BytesIO(data_gambar)
    )

    return gambar, data_gambar


# ==========================================
# MEMERIKSA WAJAH
# ==========================================

def periksa_wajah(gambar):

    lokasi_wajah = face_recognition.face_locations(
        gambar,
        model="hog"
    )

    encoding_wajah = face_recognition.face_encodings(
        gambar,
        known_face_locations=lokasi_wajah
    )

    wajah_tidak_dikenali = 0

    for encoding in encoding_wajah:

        jarak = face_recognition.face_distance(
            wajah_terdaftar,
            encoding
        )

        if len(jarak) == 0:
            wajah_tidak_dikenali += 1
            continue

        indeks_terbaik = int(np.argmin(jarak))
        jarak_terbaik = float(jarak[indeks_terbaik])

        if jarak_terbaik <= BATAS_KEMIRIPAN:

            nama = nama_terdaftar[indeks_terbaik]

            print(
                f"[DIKENALI] {nama} "
                f"(jarak={jarak_terbaik:.3f})"
            )

        else:

            wajah_tidak_dikenali += 1

            print(
                f"[TIDAK DIKENALI] "
                f"(jarak={jarak_terbaik:.3f})"
            )

    return len(encoding_wajah), wajah_tidak_dikenali


# ==========================================
# PROGRAM UTAMA
# ==========================================

def main():

    muat_wajah_terdaftar()

    email_terakhir = 0

    print("\n===================================")
    print(" SMART DOOR LOCK - FACE MONITOR")
    print("===================================")
    print("Pemantauan kamera dimulai.")
    print("Tekan CTRL+C untuk menghentikan.\n")

    while True:

        try:

            gambar, gambar_jpeg = ambil_gambar_kamera()

            jumlah_wajah, jumlah_tidak_dikenali = (
                periksa_wajah(gambar)
            )

            sekarang = time.time()

            if jumlah_tidak_dikenali > 0:

                print(
                    f"[PERINGATAN] Ditemukan "
                    f"{jumlah_tidak_dikenali} "
                    f"wajah tidak dikenali."
                )

                if sekarang - email_terakhir >= JEDA_EMAIL:

                    try:
                        kirim_email_peringatan(
                            gambar_jpeg,
                            jumlah_tidak_dikenali
                        )

                        email_terakhir = time.time()

                    except Exception as error:
                        print(
                            "[EMAIL GAGAL]",
                            error
                        )

            elif jumlah_wajah > 0:

                print(
                    "[INFO] Semua wajah pada "
                    "gambar cocok dengan data terdaftar."
                )

            else:

                print(
                    "[INFO] Tidak ada wajah terdeteksi."
                )

        except requests.RequestException as error:

            print(
                "[KAMERA] Gagal mengambil gambar:",
                error
            )

        except Exception as error:

            print(
                "[ERROR]",
                error
            )

        time.sleep(INTERVAL_CEK)


if __name__ == "__main__":

    try:
        main()

    except KeyboardInterrupt:
        print("\nProgram dihentikan.")