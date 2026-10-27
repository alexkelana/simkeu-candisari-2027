"""
SIMKEU Kecamatan Candisari 2027 — Streamlit (terhubung Google Sheets)

Persiapan:
1. Buat service account di Google Cloud, unduh JSON key.
2. Share spreadsheet "DATABASE SIMKEU KECAMATAN CANDISARI 2027"
   ke email service account (minimal Viewer untuk baca).
3. Buat file .streamlit/secrets.toml (lihat secrets.toml.example).
4. Jalankan: streamlit run app.py
"""

import streamlit as st
import pandas as pd
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

# ===================== HELPER =====================
def format_rupiah(n):
    try:
        n = float(n)
        return f"Rp {n:,.0f}".replace(",", ".")
    except Exception:
        return "-"

def is_manager(peran: str) -> bool:
    return str(peran).upper() in ("ADMIN", "KASUBAG_PEK")

def get_subkegiatan_label(kegiatan_id: str, df: pd.DataFrame) -> str:
    """Buat label yang lebih jelas untuk dropdown subkegiatan."""
    if df.empty or kegiatan_id == "-":
        return kegiatan_id
    row = df[df["kegiatan_id"] == kegiatan_id]
    if row.empty:
        return kegiatan_id
    r = row.iloc[0]
    nama = r.get("nama_kegiatan") or r.get("subkegiatan") or kegiatan_id
    sub = r.get("subkegiatan", "")
    if sub and str(sub) != str(nama):
        return f"{nama} ({sub})"
    return str(nama)

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

# ===================== USER (sementara ambil baris pertama aktif) =====================
current_user = None
if not df_pengguna.empty:
    active = df_pengguna[df_pengguna["aktif"].astype(str).str.upper() == "TRUE"]
    if not active.empty:
        current_user = active.iloc[0].to_dict()

if current_user is None:
    st.error("Tidak ada pengguna aktif ditemukan di sheet PENGGUNA.")
    st.stop()

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
        ["Dashboard", "Transaksi", "Perubahan Pagu", "Master Data"],
        label_visibility="collapsed",
    )
    st.divider()
    st.caption("Terhubung ke Google Sheets")
    if st.button("Refresh data"):
        st.cache_resource.clear()
        st.rerun()

# ===================== DASHBOARD =====================
if menu == "Dashboard":
    st.header("Dashboard")

    total_pagu = 0
    if not df_kegiatan.empty and "pagu_awal" in df_kegiatan.columns:
        total_pagu = pd.to_numeric(df_kegiatan["pagu_awal"], errors="coerce").fillna(0).sum()

    total_realisasi = 0
    if not df_transaksi.empty and "nilai" in df_transaksi.columns:
        mask = df_transaksi["status"].astype(str).str.upper().isin(["TERCATAT", "DIVERIFIKASI"])
        total_realisasi = pd.to_numeric(df_transaksi.loc[mask, "nilai"], errors="coerce").fillna(0).sum()

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

# ===================== TRANSAKSI =====================
elif menu == "Transaksi":
    st.header("Input Transaksi")

    rekening_opts = []
    if not df_rekening.empty and "kode_rekening" in df_rekening.columns:
        rekening_opts = df_rekening["kode_rekening"].dropna().tolist()

    # Cascading: pilih Kegiatan dulu, lalu Sub Kegiatan yang sesuai
    kegiatan_list = []
    if not df_kegiatan.empty and "kegiatan" in df_kegiatan.columns:
        kegiatan_list = sorted(df_kegiatan["kegiatan"].dropna().unique().tolist())

    selected_kegiatan = st.selectbox("Kegiatan", options=["-"] + kegiatan_list if kegiatan_list else ["-"])

    # Filter sub kegiatan berdasarkan kegiatan yang dipilih
    filtered_kegiatan = df_kegiatan
    if selected_kegiatan != "-" and not df_kegiatan.empty:
        filtered_kegiatan = df_kegiatan[df_kegiatan["kegiatan"] == selected_kegiatan]

    sub_opts = []
    if not filtered_kegiatan.empty and "kegiatan_id" in filtered_kegiatan.columns:
        sub_opts = filtered_kegiatan["kegiatan_id"].dropna().tolist()

    with st.form("form_transaksi"):
        col1, col2 = st.columns(2)
        with col1:
            tgl = st.date_input("Tanggal", value=date.today())
            subkegiatan = st.selectbox(
                "Sub Kegiatan",
                options=sub_opts if sub_opts else ["-"],
                format_func=lambda x: get_subkegiatan_label(x, filtered_kegiatan)
            )
            rekening = st.selectbox(
                "Kode Rekening",
                options=rekening_opts if rekening_opts else ["-"],
                format_func=lambda x: get_rekening_label(x, df_rekening)
            )
        with col2:
            nilai = st.number_input("Nilai (Rp)", min_value=0, step=1000)
            nomor_bukti = st.text_input("Nomor Bukti")
            uraian = st.text_area("Uraian", height=100)

        if st.form_submit_button("Simpan Transaksi", type="primary"):
            if not nomor_bukti or nilai <= 0 or subkegiatan == "-" or selected_kegiatan == "-":
                st.error("Kegiatan, Sub Kegiatan, nomor bukti, dan nilai positif wajib diisi.")
            else:
                st.success(f"Transaksi siap disimpan (belum diimplementasi tulis): {nomor_bukti}")
                st.warning("Fungsi tulis ke Google Sheets belum diaktifkan. Saat ini hanya baca.")

    st.divider()
    st.subheader("Daftar Transaksi")
    if not df_transaksi.empty:
        st.dataframe(df_transaksi, use_container_width=True, hide_index=True)

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
