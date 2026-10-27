# SIMKEU Streamlit — Terhubung Google Sheets

## Langkah setup service account (sekali saja)

1. Buka [Google Cloud Console](https://console.cloud.google.com/).
2. Buat project baru (atau pakai yang sudah ada).
3. Aktifkan **Google Sheets API** dan **Google Drive API**.
4. Buat Service Account → Keys → Add Key → JSON. Unduh file JSON-nya.
5. Buka spreadsheet **DATABASE SIMKEU KECAMATAN CANDISARI 2027** di Drive.
6. Klik Share → tambahkan **email service account** (ada di JSON, field `client_email`) → beri akses **Viewer** (untuk tahap baca) atau **Editor** (jika nanti mau tulis).
7. Di folder aplikasi, buat folder `.streamlit/` lalu salin `secrets.toml.example` menjadi `.streamlit/secrets.toml`.
8. Isi semua field di `secrets.toml` dari isi JSON service account.
9. Tambahkan `.streamlit/secrets.toml` ke `.gitignore`.

## Jalankan
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Status saat ini
- Sudah bisa **membaca** semua sheet utama.
- Fungsi **menulis** transaksi / perubahan pagu belum diimplementasi (sengaja, biar aman dulu).
- Autentikasi multi-user masih sederhana (ambil pengguna aktif pertama). Nanti bisa diganti login.

## Catatan keamanan
- Jangan pernah commit `secrets.toml` atau file JSON key.
- Service account hanya perlu akses ke spreadsheet ini saja.
- Validasi sisa pagu, duplikat nomor bukti, dan filter akses per peran tetap harus diimplementasikan di kode sebelum dipakai untuk data nyata.
