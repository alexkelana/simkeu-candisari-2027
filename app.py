"""
SIMKEU Kecamatan Candisari 2027 — Streamlit (terhubung Google Sheets)

Persiapan:
1. Buat service account di Google Cloud, unduh JSON key.
2. Share spreadsheet "DATABASE SIMKEU KECAMATAN CANDISARI 2027"
   ke email service account (minimal Editor untuk bisa tulis).
3. Buat file .streamlit/secrets.toml (lihat secrets.toml.example).
4. Jalankan: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import requests
from datetime import date, datetime
from streamlit_gsheets import GSheetsConnection

# ===================== KONFIG =====================
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1YzcixnxXR7B5hHh4ffVkbyKlmPscH_v-tB8Gq9cai_s/edit"

st.set_page_config(
    page_title="SIMKEU Kecamatan Candisari 2027",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ===================== KONEKSI =====================
@st.cache_resource
def get_conn():
    return st.connection("gsheets", type=GSheetsConnection)

def load_sheet(worksheet_name: str) -> pd.DataFrame:
    """Baca worksheet. Kembalikan DataFrame kosong jika gagal."""
    try:
        conn = get_conn()
        df = conn.read(spreadsheet=SPREADSHEET_URL, worksheet=worksheet_name, ttl=60)
        if df is None or df.empty:
            return pd.DataFrame()
        return df
    except Exception as e:
        st.error(f"Gagal membaca sheet '{worksheet_name}': {e}")
        st.info("Pastikan service account sudah di-share ke spreadsheet dan secrets.toml sudah benar.")
        return pd.DataFrame()

def append_transaksi(new_data: dict):
    """Tambahkan baris baru ke sheet TRANSAKSI."""
    try:
        conn = get_conn()
        df = load_sheet("TRANSAKSI")
        if df.empty:
            df = pd.DataFrame(columns=[
                "NO", "SUB KEGIATAN", "KODE REKENING BELANJA",
                "PENGELOMPOKAN BELANJA (#)", "URAIAN",
                "JENIS TRANSAKSI (UP/GU/LS)", "NOMINAL",
                "TANGGAL PENGAJUAN", "BUKTI DUKUNG SPJ", "PPTK"
            ])
        next_no = 1
        if not df.empty and "NO" in df.columns:
            nums = pd.to_numeric(df["NO"], errors="coerce").dropna()
            if not nums.empty:
                next_no = int(nums.max()) + 1

        new_data["NO"] = next_no
        new_row = pd.DataFrame([new_data])
        updated = pd.concat([df, new_row], ignore_index=True)

        conn.update(spreadsheet=SPREADSHEET_URL, worksheet="TRANSAKSI", data=updated)
        return True, next_no
    except Exception as e:
        return False, str(e)

def send_telegram(message: str) -> bool:
    """Kirim notifikasi ke Telegram. Return True jika berhasil."""
    try:
        if "telegram" not in st.secrets:
            return False
        token = st.secrets["telegram"].get("bot_token")
        chat_id = st.secrets["telegram"].get("chat_id")
        if not token or not chat_id:
            return False
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        r = requests.post(url, json=payload, timeout=10)
        return r.status_code == 200
    except Exception:
        return False

def check_login(email: str, password: str) -> bool:
    """Cek email + password dari secrets."""
    try:
        if "users" not in st.secrets:
            return False
        return st.secrets["users"].get(email) == password
    except Exception:
        return False

# ===================== HELPER =====================
def format_rupiah(n):
    try:
        n = float(n)
        return f"Rp {n:,.0f}".replace(",", ".")
    except Exception:
        return "-"

def is_manager(peran: str) -> bool:
    return str(peran).upper() in ("ADMIN", "KASUBAG_PEK")

def get_subkegiatan_label(subkode: str, df: pd.DataFrame) -> str:
    """Label dropdown: kode subkegiatan - nama kegiatan."""
    if df.empty or subkode == "-":
        return subkode
    row = df[df["subkegiatan"] == subkode]
    if row.empty:
        return subkode
    r = row.iloc[0]
    nama = r.get("nama_kegiatan", "")
    if nama:
        return f"{subkode} - {nama}"
    return str(subkode)

def get_rekening_label(kode: str, df: pd.DataFrame) -> str:
    """Tampilkan kode rekening + uraian."""
    if df.empty or kode == "-":
        return kode
    row = df[df["kode_rekening"] == kode]
    if row.empty:
        return kode
    uraian = row.iloc[0].get("uraian_rekening", "")
    if uraian:
        return f"{kode} — {uraian}"
    return str(kode)

# ===================== LOAD DATA =====================
with st.spinner("Memuat data dari Google Sheets..."):
    df_pengguna = load_sheet("PENGGUNA")
    df_wilayah = load_sheet("MASTER_WILAYAH")
    df_rekening = load_sheet("MASTER_REKENING")
    df_kegiatan = load_sheet("MASTER_KEGIATAN")
    df_transaksi = load_sheet("TRANSAKSI")
    df_perubahan = load_sheet("PERUBAHAN_PAGU")

# ===================== LOGIN =====================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.current_user = None

if not st.session_state.logged_in:
    st.title("Login SIMKEU 2027")
    st.caption("Kecamatan Candisari")
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Masuk", type="primary"):
            if check_login(email.strip(), password):
                if not df_pengguna.empty:
                    user_row = df_pengguna[df_pengguna["email"].astype(str).str.lower() == email.strip().lower()]
                    if not user_row.empty:
                        st.session_state.current_user = user_row.iloc[0].to_dict()
                        st.session_state.logged_in = True
                        st.rerun()
                    else:
                        st.error("Email tidak ditemukan di sheet PENGGUNA.")
                else:
                    st.error("Sheet PENGGUNA kosong.")
            else:
                st.error("Email atau password salah.")
    st.stop()

current_user = st.session_state.current_user

# ===================== SIDEBAR =====================
with st.sidebar:
    st.title("SIMKEU 2027")
    st.caption("Kecamatan Candisari")
    st.divider()
    st.markdown(f"**{current_user.get('nama', '-')}**")
    st.caption(str(current_user.get("peran", "")).replace("_", " "))
    st.caption(current_user.get("email", ""))
    st.divider()
    menu = st.radio(
        "Menu",
        ["Transaksi", "Dashboard", "Perubahan Pagu", "Master Data"],
        index=0,
        label_visibility="collapsed",
    )
    st.divider()
    st.caption("Terhubung ke Google Sheets")
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.current_user = None
        st.rerun()
    if st.button("Refresh data"):
        st.cache_resource.clear()
        st.rerun()

# ===================== TRANSAKSI =====================
if menu == "Transaksi":
    st.header("Input Transaksi")

    rekening_opts = []
    if not df_rekening.empty and "kode_rekening" in df_rekening.columns:
        rekening_opts = df_rekening["kode_rekening"].dropna().tolist()

    sub_opts = []
    if not df_kegiatan.empty and "subkegiatan" in df_kegiatan.columns:
        sub_opts = df_kegiatan["subkegiatan"].dropna().tolist()

    with st.form("form_transaksi"):
        col1, col2 = st.columns(2)
        with col1:
            tgl = st.date_input("Tanggal Pengajuan", value=date.today())
            subkegiatan = st.selectbox(
                "Sub Kegiatan",
                options=sub_opts if sub_opts else ["-"],
                format_func=lambda x: get_subkegiatan_label(x, df_kegiatan)
            )
            rekening = st.selectbox(
                "Kode Rekening Belanja",
                options=rekening_opts if rekening_opts else ["-"],
                format_func=lambda x: get_rekening_label(x, df_rekening)
            )
            pengelompokan = st.text_input("Pengelompokan Belanja (#)")
            jenis = st.selectbox("Jenis Transaksi", ["UP/GU", "LS"])
        with col2:
            nominal = st.number_input("Nominal (Rp)", min_value=0, step=1000)
            uraian = st.text_area("Uraian", height=100)
            bukti = st.text_input("Bukti Dukung SPJ (tautan / nomor)")

        if st.form_submit_button("Simpan Transaksi", type="primary"):
            if nominal <= 0 or subkegiatan == "-" or rekening == "-":
                st.error("Sub Kegiatan, Kode Rekening, dan Nominal wajib diisi dengan benar.")
            else:
                pptk = f"{current_user.get('nama', '')} ({current_user.get('email', '')})"
                new_data = {
                    "SUB KEGIATAN": get_subkegiatan_label(subkegiatan, df_kegiatan),
                    "KODE REKENING BELANJA": rekening,
                    "PENGELOMPOKAN BELANJA (#)": pengelompokan or "",
                    "URAIAN": uraian or "",
                    "JENIS TRANSAKSI (UP/GU/LS)": jenis,
                    "NOMINAL": nominal,
                    "TANGGAL PENGAJUAN": tgl.strftime("%d/%m/%Y"),
                    "BUKTI DUKUNG SPJ": bukti or "",
                    "PPTK": pptk,
                }
                success, result = append_transaksi(new_data)
                if success:
                    st.success(f"Transaksi berhasil disimpan ke Google Sheets. Nomor: {result}")

                    pesan = (
                        f"📌 <b>Transaksi Baru SIMKEU</b>\n"
                        f"No: {result}\n"
                        f"PPTK: {pptk}\n"
                        f"Sub Kegiatan: {new_data['SUB KEGIATAN']}\n"
                        f"Rekening: {rekening}\n"
                        f"Jenis: {jenis}\n"
                        f"Nominal: {format_rupiah(nominal)}\n"
                        f"Tanggal: {new_data['TANGGAL PENGAJUAN']}\n"
                        f"Uraian: {uraian or '-'}"
                    )
                    if send_telegram(pesan):
                        st.info("Notifikasi Telegram terkirim.")
                    else:
                        st.warning("Transaksi tersimpan, tapi notifikasi Telegram gagal (cek bot_token & chat_id di Secrets).")

                    st.cache_resource.clear()
                    st.rerun()
                else:
                    st.error(f"Gagal menyimpan: {result}")
                    st.info("Pastikan service account punya akses Editor ke spreadsheet.")

    st.divider()
    st.subheader("Daftar Transaksi")
    if not df_transaksi.empty:
        st.dataframe(df_transaksi, use_container_width=True, hide_index=True)

# ===================== DASHBOARD =====================
elif menu == "Dashboard":
    st.header("Dashboard")

    total_pagu = 0
    if not df_kegiatan.empty and "pagu_awal" in df_kegiatan.columns:
        total_pagu = pd.to_numeric(df_kegiatan["pagu_awal"], errors="coerce").fillna(0).sum()

    total_realisasi = 0
    nominal_col = None
    for col in ["NOMINAL", "nilai", "Nominal"]:
        if col in df_transaksi.columns:
            nominal_col = col
            break
    if nominal_col and not df_transaksi.empty:
        total_realisasi = pd.to_numeric(df_transaksi[nominal_col], errors="coerce").fillna(0).sum()

    sisa = total_pagu - total_realisasi
    persen = (total_realisasi / total_pagu * 100) if total_pagu else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Jumlah Sub Kegiatan", len(df_kegiatan))
    c2.metric("Total Pagu", format_rupiah(total_pagu))
    c3.metric("Realisasi", format_rupiah(total_realisasi))
    c4.metric("Sisa Pagu", format_rupiah(sisa), delta=f"{persen:.1f}% terpakai")

    st.subheader("Sub Kegiatan")
    if not df_kegiatan.empty:
        st.dataframe(df_kegiatan, use_container_width=True, hide_index=True)
    else:
        st.info("Belum ada data sub kegiatan.")

    st.subheader("Transaksi Terbaru")
    if not df_transaksi.empty:
        st.dataframe(df_transaksi, use_container_width=True, hide_index=True)
    else:
        st.info("Belum ada transaksi.")

# ===================== PERUBAHAN PAGU =====================
elif menu == "Perubahan Pagu":
    if not is_manager(current_user.get("peran", "")):
        st.warning("Menu ini hanya untuk pengelola (ADMIN / KASUBAG_PEK).")
        st.stop()

    st.header("Perubahan Pagu")
    st.info("Fungsi tulis dan approval belum diimplementasi. Saat ini hanya tampilan data.")
    if not df_perubahan.empty:
        st.dataframe(df_perubahan, use_container_width=True, hide_index=True)
    else:
        st.info("Belum ada data perubahan pagu.")

# ===================== MASTER DATA =====================
elif menu == "Master Data":
    st.header("Master Data")
    tab1, tab2, tab3, tab4 = st.tabs(["Wilayah", "Sub Kegiatan", "Rekening", "Pengguna"])
    with tab1:
        st.dataframe(df_wilayah if not df_wilayah.empty else pd.DataFrame(), use_container_width=True, hide_index=True)
    with tab2:
        st.dataframe(df_kegiatan if not df_kegiatan.empty else pd.DataFrame(), use_container_width=True, hide_index=True)
    with tab3:
        st.dataframe(df_rekening if not df_rekening.empty else pd.DataFrame(), use_container_width=True, hide_index=True)
    with tab4:
        st.dataframe(df_pengguna if not df_pengguna.empty else pd.DataFrame(), use_container_width=True, hide_index=True)

st.divider()
st.caption("SIMKEU Kecamatan Candisari 2027 · Data dari Google Sheets · Validasi dan hak akses tetap harus di backend")
